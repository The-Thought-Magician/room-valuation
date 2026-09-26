"""Pipeline 1: local open models find, identify and read everything; prices come from a
live search at run time.

1. OWLv2 proposes boxes for a general household vocabulary (not tuned to any one room).
2. Qwen3-VL-2B identifies each crop: category, name, readable brand/model, printed text.
3. Book photos also get a whole-image spine read; each spine goes to Open Library.
4. The same object seen in several photos is merged into one item.
5. Each item is priced live (prices.price_item).
"""

import difflib
import json
import re
import time
from pathlib import Path

from PIL import Image

from room_valuation import books, models, prices
from room_valuation.schema import CATEGORIES, GENRES, Book, Item, SourceResult

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
    'Example: {{"category": "monitor", "name": "computer monitor", "brand": "LG", "model": null, '
    '"size": "24 inch", "text": null, "condition": "good"}}'
)
NOT_CONTENTS = {"window", "door", "wall", "ceiling", "floor", "window grill", "doorway"}
SPINES = (
    "List every book whose spine or cover is visible in this photo, top to bottom or left to right. "
    "One line per book, exactly: title | author. Copy the printed text. If you cannot see any book, reply NONE."
)


def _iou(a, b) -> float:
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def _nms(dets: list[dict], iou: float = 0.5) -> list[dict]:
    kept = []
    for d in sorted(dets, key=lambda d: -d["score"]):
        if all(_iou(d["box"], k["box"]) < iou for k in kept):
            kept.append(d)
    return kept


def _crop(image: Image.Image, box, margin: float = 0.1) -> Image.Image:
    w, h = image.size
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    c = image.crop((int(max(0, x0 - margin * bw) * w), int(max(0, y0 - margin * bh) * h),
                    int(min(1, x1 + margin * bw) * w), int(min(1, y1 + margin * bh) * h)))
    c.thumbnail((768, 768))
    return c


def _json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}


def _null(v):
    """Drop empty answers and the placeholder text a small model sometimes copies back."""
    if v is None:
        return None
    s = str(v).strip()
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


def _same(a: Item, b: Item) -> bool:
    if a.category != b.category:
        return False
    shared = set(a.photos) & set(b.photos)
    if shared:  # in one photo: the same object only if the boxes overlap heavily
        return any(_contain(ra["box"], rb["box"]) > 0.45 for ra in a.regions for rb in b.regions
                   if ra["photo"] == rb["photo"])  # 0.45: a screen box inside its monitor box
    if a.category == "book":
        ta, tb = (a.book.title if a.book else a.name), (b.book.title if b.book else b.name)
        return _similar(ta or "", tb or "") > 0.7
    if a.brand and b.brand and a.brand.lower() != b.brand.lower():
        return False
    return (a.brand and b.brand) or _similar(a.name, b.name) > 0.6


def _merge(items: list[Item]) -> list[Item]:
    groups: list[Item] = []
    for it in items:
        home = next((g for g in groups if _same(g, it)), None)
        if home is None:
            groups.append(it)
            continue
        home.photos = sorted(set(home.photos) | set(it.photos))
        home.regions += it.regions
        for key in ("brand", "model", "evidence"):
            if not getattr(home, key) and getattr(it, key):
                setattr(home, key, getattr(it, key))
        home.attributes = {**it.attributes, **home.attributes}
    return groups


def detect_and_identify(photos: list[tuple[Path, str]], threshold: float = 0.18,
                        max_boxes: int = 14) -> tuple[list[Item], list[dict]]:
    det = models.Detector()
    raw = []
    for path, tag in photos:
        image = Image.open(path).convert("RGB")
        boxes = _nms(det.detect(image, PROMPTS, threshold))
        area_ok = [b for b in boxes if (b["box"][2] - b["box"][0]) * (b["box"][3] - b["box"][1]) > 0.004]
        raw.append((path, tag, area_ok[:max_boxes]))
    del det
    models.free()

    vlm = models.VLM()
    items, log = [], []
    n = 0
    for path, tag, boxes in raw:
        image = Image.open(path).convert("RGB")
        for b in boxes:
            hint = PROMPT_CATEGORY[b["prompt"]]
            if hint == "book":
                continue  # books are read from the whole photo below, box crops cut titles in half
            ans = _json(vlm.ask(IDENTIFY.format(categories=", ".join(CATEGORIES), hint=b["prompt"]), _crop(image, b["box"]), 160))
            cat = ans.get("category") if ans.get("category") in CATEGORIES else hint
            name = _null(ans.get("name")) or b["prompt"][2:]
            if cat == "book" or name.lower() in NOT_CONTENTS:
                continue
            attrs = {"size": s} if (s := _null(ans.get("size"))) else {}
            items.append(Item(id=f"local-{n}", source="local", category=cat, name=name,
                              brand=_null(ans.get("brand")), model=_null(ans.get("model")), attributes=attrs,
                              condition=ans.get("condition") if ans.get("condition") in prices.CONDITION_LIFE_USED else None,
                              evidence=_null(ans.get("text")), photos=[path.name],
                              regions=[{"photo": path.name, "box": [round(x, 4) for x in b["box"]]}]))
            log.append({"photo": path.name, "detector": b, "vlm": ans})
            n += 1
        if tag == "books" or any(PROMPT_CATEGORY[b["prompt"]] == "book" for b in boxes):
            reply = vlm.ask(SPINES, _downsize(image), 400)
            log.append({"photo": path.name, "spines": reply})
            for line in reply.splitlines():
                if "|" not in line or line.strip().upper() == "NONE":
                    continue
                title, _, author = (s.strip(" -*•\t") for s in line.partition("|"))
                if len(title) < 2:
                    continue
                found = books.lookup(f"{title} {author}")
                book = found or Book(title=title, author=author or None, lookup="spine text only")
                items.append(Item(id=f"local-{n}", source="local", category="book", name=book.title or title,
                                  evidence=line.strip(), photos=[path.name], book=book))
                n += 1
    del vlm
    models.free()
    return _merge(items), log


def _downsize(image: Image.Image, side: int = 1280) -> Image.Image:
    im = image.copy()
    im.thumbnail((side, side))
    return im


def query_for(item: Item) -> tuple[str, list[str]]:
    """Search text and words a listing title must contain."""
    if item.category == "book" and item.book and item.book.title:
        return f"{item.book.title} {item.book.author or ''} book".strip(), []
    parts = [item.brand, item.model, item.attributes.get("size"), item.name]
    must = [item.brand] if item.brand else []
    return " ".join(p for p in parts if p), [m.split()[0] for m in must]


def run(photos: list[tuple[Path, str]], workdir: Path) -> SourceResult:
    t0 = time.time()
    items, log = detect_and_identify(photos)
    for it in items:
        q, must = query_for(it)
        p = prices.price_item(q, it.category, must)
        it.rcv_inr = p.get("rcv_inr")
        it.price_source = p.get("url")
        it.price_note = (f"median of {p['matched']} matching listings for '{q}'"
                         + (f" ({', '.join(p['sellers'])})" if p.get("sellers") else "")) if it.rcv_inr else p.get("note")
        log.append({"item": it.id, "price": p})
        if it.book and it.book.genre not in GENRES:
            it.book.genre = "other"
    (workdir / "local_log.json").write_text(json.dumps(log, indent=1, default=str))
    shelves = sum(1 for it in items if "shelf" in it.name.lower())
    return SourceResult(source="local", items=items, shelves=shelves, seconds=round(time.time() - t0, 1),
                        notes=[f"{len(items)} items after merging repeats across photos"])
