"""Pipeline 1: local open models find, identify and read everything; prices come from a
live search at run time.

1. OWLv2 proposes boxes for a general household vocabulary (not tuned to any one room).
2. Qwen3-VL-2B identifies each crop: category, name, readable brand/model, printed text.
3. Book photos: PP-OCR (RapidOCR) reads the spines, Qwen3-VL reads them too as a cross-check,
   and each spine text goes to Open Library.
4. The same object seen in several photos is merged into one item: by its 3D position when the
   photos could be reconstructed (geometry.py), otherwise by box overlap and name.
5. Each item is priced live from its own reading (prices.query_for and price_item), so Jev
   can rank this pipeline's value against the frontier model's and the owner's. Anything
   still unpriced after Jev gets a second search in market.py.
"""

import difflib
import json
import re
import statistics
import time
from pathlib import Path

from PIL import Image

from room_valuation import books, geometry, models, ocr, prices, specs
from room_valuation.schema import CATEGORIES, GENRES, Book, Item, SourceResult, json_object

VOCAB = {
    "laptop": ["a laptop", "a notebook computer"],
    "monitor": ["a computer monitor", "a television", "a display screen"],
    "computer_accessory": ["a keyboard", "a computer mouse", "a webcam", "a laptop stand", "a charger", "a hard disk"],
    "phone": ["a mobile phone", "a tablet"],
    "audio": ["headphones", "earphones", "a speaker"],
    "networking": ["a wifi router", "a modem"],
    "appliance": ["an air conditioner", "an air cooler", "a table fan", "a ceiling fan", "an iron", "a kettle",
                  "a refrigerator", "a room heater", "a printer"],
    "lighting": ["a tube light", "a light bulb", "a lamp"],
    "electrical_fixture": ["a light switch board", "an electrical socket", "an extension board", "a fan regulator"],
    "furniture": ["a bed", "a table", "a desk", "a chair", "a wardrobe", "a cupboard", "a shelf", "a bookshelf",
                  "a drawer", "a sofa", "a stool"],
    "bedding": ["a mattress", "a pillow", "a blanket", "a bedsheet"],
    "book": ["a book", "a stack of books", "a book spine"],
    "decor": ["a mirror", "a wall clock", "a curtain", "a photo frame", "a plant pot", "a poster"],
    "building_fixture": ["a door", "a window"],
    "kitchenware": ["a water bottle", "a coffee mug", "a cup", "a plate", "a lunch box"],
    "bag_clothing": ["a backpack", "a bag", "shoes", "clothes"],
}
PROMPTS = [p for ps in VOCAB.values() for p in ps]
PROMPT_CATEGORY = {p: c for c, ps in VOCAB.items() for p in ps}

IDENTIFY = (
    "This is a crop from a photo of a room in India. The detector thinks it shows {hint}. "
    "Identify the main object. Reply with one JSON object and nothing else, with keys: "
    "category (one of: {categories}), name (short generic name), brand (only if a logo or name is readable), "
    "model (only if model text is readable), size (only if you can tell), text (text printed on it), "
    "condition (like_new, good, fair or poor). Use null for anything you cannot see. "
    'Example: {{"category": "kitchenware", "name": "pressure cooker", "brand": "Prestige", "model": null, '
    '"size": "5 litre", "text": null, "condition": "good"}}'
)
NOT_CONTENTS = {"wall", "ceiling", "floor", "doorway"}
SPINES = (
    "List every book whose spine or cover is visible in this photo, top to bottom or left to right. "
    "One line per book, exactly: title | author. Copy the printed text. If you cannot see any book, reply NONE."
)


def _nms(dets: list[dict], iou: float = 0.5) -> list[dict]:
    """Class-agnostic non-maximum suppression, best score first."""
    import torch
    from torchvision.ops import nms

    if not dets:
        return []
    keep = nms(torch.tensor([d["box"] for d in dets]), torch.tensor([d["score"] for d in dets]), iou)
    return [dets[i] for i in keep.tolist()]


def _crop(image: Image.Image, box, margin: float = 0.1) -> Image.Image:
    w, h = image.size
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    c = image.crop((int(max(0, x0 - margin * bw) * w), int(max(0, y0 - margin * bh) * h),
                    int(min(1, x1 + margin * bw) * w), int(min(1, y1 + margin * bh) * h)))
    c.thumbnail((768, 768))
    return c


# values from the prompts' own examples: a small model sometimes copies them back as answers
# (the laptop got "specs: 1400 W" from the air-fryer example, 2026-09-26)
EXAMPLE_VALUES = {"prestige", "pressure cooker", "5 litre", "philips", "hd9252", "4.1 litre", "1400 w", "air fryer"}


def _null(v):
    """Drop empty answers, placeholder text and prompt examples a small model copies back."""
    if v is None:
        return None
    s = str(v).strip()
    if s.lower() in EXAMPLE_VALUES:
        return None
    if s.lower() in ("", "null", "none", "unknown", "n/a", "standard") or any(
            w in s.lower() for w in ("else null", "if you can", "readable", "if a logo")):
        return None
    return s


def _similar(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _contain(a, b) -> float:
    """Intersection over the smaller box: 1 when one box sits inside the other."""
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    small = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))
    return ix * iy / small if small > 0 else 0.0


def _near(a: dict, b: dict) -> tuple[float, float]:
    """Distance between two measured objects, and how close counts as one place: a quarter metre,
    or 40 percent of the bigger object's larger side."""
    side = max(a["width_cm"], a["height_cm"], b["width_cm"], b["height_cm"]) / 100
    return geometry.distance(a, b), max(0.25, 0.4 * side)


def _same(a: Item, b: Item) -> bool:
    if a.category != b.category:
        return False
    if a.category == "book":
        ta, tb = (a.book.title if a.book else a.name), (b.book.title if b.book else b.name)
        return _similar(ta or "", tb or "") > 0.7
    if a.measured and b.measured:  # 3D first: one place and one size is one object, whatever each view called it
        d, near = _near(a.measured, b.measured)
        brands_differ = a.brand and b.brand and a.brand.lower() != b.brand.lower()
        side_a = max(a.measured["width_cm"], a.measured["height_cm"])
        side_b = max(b.measured["width_cm"], b.measured["height_cm"])
        alike = max(side_a, side_b) <= 2.5 * max(1, min(side_a, side_b))  # a pillow on the bed is not the bed
        if d <= near and alike and not brands_differ:
            return True
        if d > max(1.0, 3 * near):  # two curtains, two chairs: same name, different places
            return False
    shared = set(a.photos) & set(b.photos)
    if shared:  # in one photo: the same object only if the boxes overlap heavily
        return any(_contain(ra["box"], rb["box"]) > 0.45 for ra in a.regions for rb in b.regions
                   if ra["photo"] == rb["photo"])  # 0.45: a screen box inside its monitor box
    if a.brand and b.brand and a.brand.lower() != b.brand.lower():
        return False
    return (a.brand and b.brand) or _similar(a.name, b.name) > 0.6


def _merge(items: list[Item], geo: geometry.Geometry | None = None) -> list[Item]:
    groups: list[Item] = []
    for it in items:
        home = next((g for g in groups if _same(g, it)), None)
        if home is None:
            groups.append(it)
            continue
        home.photos = sorted(set(home.photos) | set(it.photos))
        home.regions += it.regions
        if geo:  # re-measure from every view it now has
            home.measured = geo.locate(home.regions) or home.measured
        for key in ("brand", "model", "evidence"):
            if not getattr(home, key) and getattr(it, key):
                setattr(home, key, getattr(it, key))
        home.attributes = {**it.attributes, **home.attributes}
    return groups


def detect(photos: list[tuple[Path, str]], progress=None, threshold: float = 0.18,
           max_boxes: int = 14, workdir: Path | None = None) -> tuple[list[Item], list[dict]]:
    """The item list for the owner to review: every detected object, identified from its crop,
    placed and measured in 3D when the photos reconstruct. Book boxes become one 'books' card
    whose spines are read later from close-ups."""
    say = progress or (lambda **kw: None)
    det = models.Detector()
    raw = []
    for i, (path, tag) in enumerate(photos):
        say(step="finding objects", done=i, total=len(photos))
        image = Image.open(path).convert("RGB")
        boxes = _nms(det.detect(image, PROMPTS, threshold))
        area_ok = [b for b in boxes if (b["box"][2] - b["box"][0]) * (b["box"][3] - b["box"][1]) > 0.004]
        raw.append((path, tag, area_ok[:max_boxes]))
    del det
    models.free()
    geo = None
    if workdir is not None:  # between the two models, so VGGT has the card to itself
        say(step="placing objects in 3D", done=0, total=1)
        geo = geometry.reconstruct([p for p, _ in photos], workdir)

    vlm = models.VLM()
    items, log = [], []
    n = 0
    total = sum(len(b) for _, _, b in raw)
    for path, _tag, boxes in raw:
        image = Image.open(path).convert("RGB")
        for b in boxes:
            say(step="identifying objects", done=n, total=total)
            region = [{"photo": path.name, "box": [round(x, 4) for x in b["box"]]}]
            hint = PROMPT_CATEGORY[b["prompt"]]
            if hint == "book":
                items.append(Item(id=f"local-{n}", source="local", category="book", name="books",
                                  photos=[path.name], regions=region))
                n += 1
                continue
            prompt = IDENTIFY.format(categories=", ".join(CATEGORIES), hint=b["prompt"])
            ans = json_object(vlm.ask(prompt, _crop(image, b["box"]), 160))
            cat = ans.get("category") if ans.get("category") in CATEGORIES else hint
            name = _null(ans.get("name")) or b["prompt"][2:]
            if name.lower() in NOT_CONTENTS:
                continue
            if cat == "book":
                name = "books"
            attrs = {"size": s} if (s := _null(ans.get("size"))) else {}
            items.append(Item(id=f"local-{n}", source="local", category=cat, name=name,
                              brand=_null(ans.get("brand")), model=_null(ans.get("model")), attributes=attrs,
                              condition=ans.get("condition") if ans.get("condition") in prices.CONDITION_LIFE_USED else None,
                              evidence=_null(ans.get("text")), photos=[path.name], regions=region,
                              measured=geo.locate(region) if geo else None))
            log.append({"photo": path.name, "detector": b, "vlm": ans})
            n += 1
    del vlm
    models.free()
    return _merge(items, geo), log + ([{"geometry": geometry.summary(geo)}] if geo else [])


SMALL_PRINT = {"laptop", "monitor", "phone", "computer_accessory", "networking", "appliance", "audio"}
CLOSEUP = (
    "This is a close-up photo of {name}, taken to show its label, logo or model sticker. "
    "Text read by OCR: {ocr}. Reply with one JSON object and nothing else, with keys: brand, model "
    "(model number exactly as printed), serial (serial number exactly as printed, often after S/N or SN), "
    "size (e.g. 27 inch, 1.5 ton), specs (resolution, capacity, power, anything printed), "
    "name (short generic name). Use null for anything not shown. "
    'Example: {{"brand": "Philips", "model": "HD9252", "serial": null, "size": "4.1 litre", "specs": "1400 W", '
    '"name": "air fryer"}}'
)


def _on_label(value: str, ocr_text: str) -> bool:
    """A model or serial number the VLM claims, found in the OCR text (spaces and case aside):
    the small model sometimes invents model numbers, the OCR only reads what is printed."""
    squash = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())  # noqa: E731
    v = squash(value)
    return len(v) >= 4 and v in squash(ocr_text)


def refine(entries: list[dict], closeups: dict[str, list[Path]], room_photos: dict[str, Path],
           progress=None) -> tuple[list[Item], list[dict]]:
    """The reviewed item list, sharpened by each item's close-ups: OCR and the VLM read labels
    and model stickers; book cards turn into one item per spine."""
    say = progress or (lambda **kw: None)
    vlm = models.VLM()
    items, log = [], []
    for k, e in enumerate(entries):
        say(step="reading close-ups", done=k, total=len(entries))
        if e["state"] == "added":
            it = Item(id=e["id"], source="local", category=e["category"], name=e["name"], evidence="added by the owner")
        else:
            it = Item.model_validate(e["detected"])
        it.quantity = int(e.get("quantity") or it.quantity or 1)
        shots = closeups.get(e["id"], [])
        if it.category == "book":
            images = [(p.name, Image.open(p).convert("RGB")) for p in shots]
            if not images:  # no close-up: one crop per room photo around all its book boxes
                by_photo: dict[str, list] = {}
                for r in it.regions:
                    by_photo.setdefault(r["photo"], []).append(r["box"])
                for photo, boxes in by_photo.items():
                    if photo in room_photos:
                        images.append((photo, _union_crop(Image.open(room_photos[photo]).convert("RGB"), boxes)))
            books_found = []
            for photo, image in images:
                for book, evidence in _read_spines(image, vlm, photo, log):
                    books_found.append(Item(id=f"{e['id']}-b{len(books_found)}", source="local", category="book",
                                            name=book.title, evidence=evidence, photos=[photo], book=book))
            items.extend(_settle_books(_dedupe_books(books_found), it) )
            continue
        for p in shots:
            image = Image.open(p).convert("RGB")
            # small print matters where a model number or configuration sets the price
            text = ocr.read_small_text(image) if it.category in SMALL_PRINT else ocr.read_text(image)
            ans = json_object(vlm.ask(CLOSEUP.format(name=it.name, ocr=text or "nothing"), _downsize(image), 200))
            log.append({"item": it.id, "closeup": p.name, "ocr": text, "vlm": ans})
            ids = specs.label_ids(text)  # rules on the OCR text: the VLM mixed up model, radio module and serial
            ruled = it.attributes.get("model_read_by") == "label rules"  # by an earlier close-up of this item
            if _null(ans.get("brand")):
                it.brand = _null(ans.get("brand"))
            if _null(ans.get("model")) and not ruled and not ids.get("model"):
                it.model = _null(ans.get("model"))
            if ids.get("model") and not ruled:
                it.model = ids["model"]
                it.attributes["model_read_by"] = "label rules"
            if it.model and _on_label(it.model, text):  # prices.lookup then searches this exact model
                it.attributes["model_source"] = "read off the label"
            for key in ("product_id", "serial"):
                if ids.get(key):
                    it.attributes[key] = ids[key]
            if "serial" not in it.attributes and (serial := _null(ans.get("serial"))) and _on_label(serial, text):
                it.attributes["serial"] = serial
            read = specs.parse(text, it.category)  # the configuration, from the OCR text only
            if read:
                it.attributes |= read | {"spec_source": "read off the label"}
            for key in ("size", "specs"):
                if _null(ans.get(key)):
                    it.attributes[key] = _null(ans.get(key))
            it.evidence = "; ".join(x for x in (it.evidence, f"label: {text}" if text else None) if x)
            it.photos.append(p.name)
        items.append(it)
    del vlm
    models.free()
    return items, log


MIN_MATCH = 0.6  # half similarity, half title coverage; below this it is probably a different book


PUBLISHERS = {"doubleday", "picador", "vintage", "penguin", "harpercollins", "harper", "bloomsbury", "pan",
              "macmillan", "random", "house", "books", "edition", "updated", "new", "york", "times", "best", "seller",
              "classics", "press", "publishing", "xx", "the", "and", "of"}


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def _plausible_spine(text: str) -> bool:
    """Unmatched spine text worth keeping as a book: two real words that are not only
    publisher or edition words (DOUBLEDAY, PICADOR XX, NEW UPDATED EDITION)."""
    words = [w for w in _norm(text).split() if len(w) >= 3]
    return len(words) >= 2 and any(w not in PUBLISHERS for w in words) and len(_norm(text)) >= 8


def _vlm_spine_queries(reply: str) -> list[str]:
    """Qwen lists books as 'title | author', sometimes several per line, sometimes looping
    the same field. Split into pairs, drop repeats, cap the loop."""
    out = []
    for line in reply.splitlines():
        if line.strip().upper() == "NONE" or "|" not in line:
            continue
        fields, seen = [], set()
        for f in (s.strip(" -*•\t") for s in line.split("|")):
            if f and f.lower() not in seen:
                fields.append(f)
                seen.add(f.lower())
            if len(fields) >= 24:
                break
        for i in range(0, len(fields), 2):
            q = " ".join(fields[i:i + 2]).strip()
            if len(q) >= 3:
                out.append(q)
    return out


def _fuzzy_words(a: set[str], b: set[str]) -> int:
    """Words of a that appear in b, allowing one OCR slip (Forment for Torment)."""
    return sum(1 for w in a if w in b or any(_similar(w, v) >= 0.8 for v in b))


def _same_book(a: Book, b: Book) -> bool:
    ta, tb = _norm(a.title), _norm(b.title)
    if not ta or not tb:
        return False
    if a.isbn and a.isbn == b.isbn:
        return True
    ca, cb = ta.replace(" ", ""), tb.replace(" ", "")  # OCR runs words together: ROCKPAPERSCISSORS
    if ca == cb or (min(len(ca), len(cb)) >= 6 and (ca in cb or cb in ca)) or _similar(ta, tb) > 0.75:
        return True
    wa = {w for w in _norm(f"{a.title} {a.author or ''}").split() if len(w) >= 4 and w not in PUBLISHERS}
    wb = {w for w in _norm(f"{b.title} {b.author or ''}").split() if len(w) >= 4 and w not in PUBLISHERS}
    small = min(len(wa), len(wb))
    # an author in common is not enough: two Shakespeare plays are two books
    title_a = {w for w in ta.split() if len(w) >= 4 and w not in PUBLISHERS}
    title_b = {w for w in tb.split() if len(w) >= 4 and w not in PUBLISHERS}
    titles_meet = _fuzzy_words(title_a, wb) >= 1 or _fuzzy_words(title_b, wa) >= 1
    return titles_meet and small >= 2 and _fuzzy_words(wa, wb) >= max(2, round(0.6 * small))


def _ocr_supports(book: Book, ocr_words: set[str]) -> bool:
    """The OCR reads what is printed; the small VLM sometimes names books that are not there.
    A title stays only if one of its real words (or a near miss) is in the OCR text."""
    words = {w for w in _norm(book.title).split() if len(w) >= 4 and w not in PUBLISHERS}
    compact = "".join(sorted(ocr_words))
    hits = sum(1 for w in words if _fuzzy_words({w}, ocr_words) or w in compact)
    return not words or hits >= max(1, (len(words) + 1) // 2)  # half the title, not one lucky word


def _read_spines(image: Image.Image, vlm, photo: str, log: list) -> list[tuple[Book, str]]:
    """Spine texts from PP-OCR and from the VLM, each looked up in Open Library. A catalogue
    match wins; unmatched text is kept only if it looks like a real title; repeats collapse."""
    ocr_reads = ocr.spines(image)
    ocr_words = {w for s in ocr_reads for w in _norm(s["text"]).split() if len(w) >= 3}
    ocr_words |= {"".join(_norm(s["text"]).split()) for s in ocr_reads}  # run-together reads
    texts = [(f"ocr: {s['text']}", s["text"]) for s in ocr_reads]
    texts += [(f"vlm: {q}", q) for q in _vlm_spine_queries(vlm.ask(SPINES, _downsize(image), 400))]
    log.append({"photo": photo, "spine_texts": [e for e, _ in texts]})
    found, dropped = [], []
    for evidence, query in texts:
        book = books.lookup(query)
        if book and (book.match or 0) >= MIN_MATCH:
            cand = book
        elif _plausible_spine(query):
            cand = Book(title=query, lookup="spine text only", match=book.match if book else None)
        else:
            continue
        if evidence.startswith("vlm:") and ocr_reads and not _ocr_supports(cand, ocr_words):
            dropped.append(f"{cand.title} ({evidence})")
            continue
        found.append((cand, evidence))
    if dropped:
        log.append({"photo": photo, "dropped_without_ocr_support": dropped})
    kept: list[tuple[Book, str]] = []
    for book, ev in sorted(found, key=lambda f: -(f[0].match or 0)):
        twin = next((k for k in kept if _same_book(k[0], book)), None)
        if twin is None:
            kept.append((book, ev))
        else:
            kept[kept.index(twin)] = (twin[0], f"{twin[1]}; {ev}")
    return kept


def _dedupe_books(items: list[Item]) -> list[Item]:
    """The same book read in two photos, or once by OCR and once by the VLM, is one book."""
    kept: list[Item] = []
    for it in sorted(items, key=lambda i: -((i.book.match or 0) if i.book else 0)):
        twin = next((k for k in kept if k.book and it.book and _same_book(k.book, it.book)), None)
        if twin is None:
            kept.append(it)
        else:
            twin.photos = sorted(set(twin.photos) | set(it.photos))
            twin.evidence = "; ".join(x for x in (twin.evidence, it.evidence) if x)
    return kept


def _settle_books(found: list[Item], card: Item) -> list[Item]:
    """Catalogue-matched books stay. Unmatched spine text that shares a word with a matched
    book is a partial read of it and goes. What is left is an unidentified book each."""
    matched = [b for b in found if b.book and b.book.lookup == "openlibrary"]
    known = set()
    for b in matched:
        known |= {w for w in _norm(f"{b.book.title} {b.book.author or ''}").split() if len(w) >= 4 and w not in PUBLISHERS}
    titles = ["".join(_norm(b.book.title).split()) for b in matched]
    rest = []
    for b in found:
        if b in matched:
            continue
        words = {w for w in _norm(b.name).split() if len(w) >= 4 and w not in PUBLISHERS}
        if words and _fuzzy_words(words, known) >= 1:
            continue
        # letters run together or cut off
        if any(_partial_read("".join(_norm(b.name).split()), t) for t in titles):
            continue
        rest.append(b.model_copy(update={"name": "unidentified book", "evidence": f"spine read as: {b.name}"}))
    return matched + rest or [card.model_copy(update={"name": "book (title not read)"})]


def _partial_read(fragment: str, title: str) -> bool:
    """A long run of letters shared with a known title: most of the fragment, or most of the title
    ('RONHORSE EDWARD MARSTON' is Iron Horse, 'AND CL20PXCIA' is Antony and Cleopatra)."""
    run = difflib.SequenceMatcher(None, fragment, title).find_longest_match(0, len(fragment), 0, len(title)).size
    return run >= 5 and (run >= 0.4 * len(fragment) or run >= 0.7 * len(title))


def _union_crop(image: Image.Image, boxes: list[list[float]], margin: float = 0.15, side: int = 2000) -> Image.Image:
    """One crop around every book box in a photo, at full resolution: overlapping crops of
    one shelf read each spine many times."""
    x0, y0 = min(b[0] for b in boxes), min(b[1] for b in boxes)
    x1, y1 = max(b[2] for b in boxes), max(b[3] for b in boxes)
    w, h = image.size
    bw, bh = x1 - x0, y1 - y0
    c = image.crop((int(max(0, x0 - margin * bw) * w), int(max(0, y0 - margin * bh) * h),
                    int(min(1, x1 + margin * bw) * w), int(min(1, y1 + margin * bh) * h)))
    c.thumbnail((side, side))
    return c


def _downsize(image: Image.Image, side: int = 1280) -> Image.Image:
    im = image.copy()
    im.thumbnail((side, side))
    return im


def price_items(items: list[Item], log: list) -> None:
    """This pipeline's own value for each item: one Serper search from its own reading. A spine
    nobody could read gets the median of the identified books' prices."""
    unread = [it for it in items if it.category == "book" and (not it.book or it.book.lookup != "openlibrary")]
    for it in items:
        if it.book and it.book.genre not in GENRES:
            it.book.genre = "other"
        if it not in unread:
            it.rcv_inr, it.price_source, it.price_note, raw = prices.lookup(it)
            prices.take(it, raw)
            log.append({"item": it.id, "price": raw})
    known = [it.rcv_inr for it in items if it.category == "book" and it not in unread and it.rcv_inr]
    for it in unread:
        it.rcv_inr = statistics.median_high(known) if known else None
        it.price_note = f"median of the {len(known)} identified books in this room" if known else "no identified books to compare"


def value(entries: list[dict], closeups: dict[str, list[Path]], room_photos: dict[str, Path], workdir: Path,
          progress=None, reuse_refined: bool = False) -> SourceResult:
    t0 = time.time()
    refined = workdir / "local_refined.json"
    if reuse_refined and refined.exists():  # tuning prices or Jev: skip the GPU work
        saved = json.loads(refined.read_text())
        items, log = [Item.model_validate(i) for i in saved["items"]], saved["log"]
    else:
        items, log = refine(entries, closeups, room_photos, progress)
        refined.write_text(json.dumps({"items": [i.model_dump() for i in items], "log": log}, default=str))
    price_items(items, log)
    (workdir / "local_log.json").write_text(json.dumps(log, indent=1, default=str))
    shelves = sum(it.quantity for it in items if "shelf" in it.name.lower())
    return SourceResult(source="local", items=items, shelves=shelves, seconds=round(time.time() - t0, 1),
                        notes=[f"{len(items)} items after the owner's review and close-ups"])
