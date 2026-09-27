"""Pipeline 2: a frontier vision model reads the photos, identifies and prices everything.

Two backends behind one function:
- "opus": Claude Opus 5.5 through `claude -p` (Claude Code headless), with Read for
  the photos and WebSearch/WebFetch for live Indian prices.
- "astra": GPT-6 Astra through the OpenAI Responses API with the web_search tool.
The brief asked for Astra; Opus stands in until Astra credits exist.
"""

import base64
import json
import os
import re
import subprocess
import time
from pathlib import Path

import httpx

from room_valuation import specs
from room_valuation.schema import CATEGORIES, GENRES, Book, Item, SourceResult, number

PROMPT = """You are valuing the contents of a room in {city}, India, for a home insurance claim.
Photos (read every one with the Read tool; tag = what the photographer meant it to show):
{photo_list}

Build one deduplicated inventory of every distinct physical object worth more than about Rs 50:
electronics, furniture, bedding, books, decor, appliances, lights, fans, and electrical fixtures.
Also list the building's own fixtures, which insurers cover under the building policy: every door (with
its frame and hardware) and every window (with frame, glass and grill) as category building_fixture,
with estimated size and material; price each as supply plus installation.
The same object seen in several photos is one item. Two identical objects are one item with quantity 2.

Rules:
- category must be one of: {categories}
- Books: read each spine. Give title and author exactly as printed, isbn only if visible,
  genre one of: {genres}. One item per book.
- Monitors and TVs: read the model sticker or any resolution shown on screen (a settings page or the
  monitor's info menu). If you have the model, look up its resolution, panel and refresh rate. Never
  claim a resolution you did not read or look up; say "resolution unknown" instead.
- Brand and model: only what you can read or clearly recognise. If you cannot read the model,
  describe the class instead (for a monitor: diagonal in inches estimated against nearby objects,
  resolution class HD/FHD/QHD/UHD, panel type) and put your reasoning in price_note.
- Switchboards: one item per board, attributes must list how many switch, socket and regulator
  modules you can count, and the plate size (e.g. 8M).
- Model and serial stickers: read every label you can. Put a model number in model, and a serial
  number in attributes as "serial". An insurer uses them to confirm the exact item.
- Laptops, desktops, phones and tablets: the price depends on the configuration. Read the CPU,
  GPU, RAM and storage from any sticker, label, box or screen showing system information, and put
  them in attributes as "cpu", "gpu", "ram", "storage". Only what you can read; never guess a
  configuration, and price the configuration you read.
- Prices: search the web for the current price to buy the item NEW in India (Amazon.in, Flipkart,
  Croma, Reliance Digital, brand sites; books: Amazon.in, Flipkart, Bookswagon). rcv_inr is per unit,
  in rupees. price_source is the URL you used. price_kind is "exact" when you identified this exact
  model and priced it, "closest" when you priced the closest equivalent (say what and why in
  price_note), "estimate" when no page gave a price (then price_source is "estimate"). Price like
  kind and quality: the same type, size and grade, not the cheapest item of the category. Never
  leave rcv_inr empty.
- product_size: the size of the product you priced, as its listing states it (e.g. "24 inch",
  "90 x 60 cm", "6 x 3 ft"), or null.
- condition: one of like_new, good, fair, poor, from visible wear.
- Also estimate the room floor area in square metres from what the photos show, and count shelves.

Reply with ONLY a JSON object, no prose, no code fence:
{{"items": [{{"category": "", "name": "", "brand": null, "model": null, "attributes": {{}},
  "quantity": 1, "condition": "good", "evidence": "text you read on it, if any",
  "photos": ["file names where it appears"], "book": null or {{"title": "", "author": "", "isbn": null, "genre": ""}},
  "rcv_inr": 0, "price_kind": "exact", "price_source": "", "price_note": "", "product_size": null}}],
 "room_area_m2": 0, "shelves": 0, "notes": ["anything the insurer should know"]}}
"""


def _photo_list(photos: list[tuple[Path, str]]) -> str:
    return "\n".join(f"- {p} (tag: {tag})" for p, tag in photos)


def _parse(text: str) -> dict:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1)
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start : end + 1])


def _to_result(data: dict, source: str, seconds: float) -> SourceResult:
    items = []
    for i, raw in enumerate(data.get("items", [])):
        cat = raw.get("category") if raw.get("category") in CATEGORIES else "other"
        book = None
        if cat == "book" and raw.get("book"):
            b = raw["book"]
            book = Book(title=b.get("title"), author=b.get("author"), isbn=b.get("isbn"),
                        genre=b.get("genre") if b.get("genre") in GENRES else "other", lookup=source)
        attrs = {str(k): str(v) for k, v in (raw.get("attributes") or {}).items()}
        read = specs.parse(" ".join(str(x) for x in (raw.get("evidence"), raw.get("model"), *attrs.values()) if x), cat)
        if read:  # the configuration it read, in the same keys and form as the local pipeline's
            attrs |= {k: v for k, v in read.items() if k not in attrs or k in specs.PRICE_KEYS}
            attrs["spec_source"] = "the frontier model's reading"
        items.append(Item(
            id=f"{source}-{i}", source=source, category=cat, name=raw.get("name") or cat,
            brand=raw.get("brand"), model=raw.get("model"),
            attributes=attrs,
            quantity=int(raw.get("quantity") or 1), condition=raw.get("condition"),
            evidence=raw.get("evidence"), photos=[Path(p).name for p in raw.get("photos") or []],
            book=book, rcv_inr=number(raw.get("rcv_inr")), price_source=raw.get("price_source"),
            price_note=raw.get("price_note"),
            price_kind=raw.get("price_kind") if raw.get("price_kind") in ("exact", "closest", "estimate") else None,
            product_size=str(raw["product_size"]) if raw.get("product_size") else None,
        ))
    return SourceResult(source=source, items=items, room_area_m2=number(data.get("room_area_m2")),
                        shelves=int(data["shelves"]) if data.get("shelves") is not None else None,
                        notes=data.get("notes") or [], seconds=round(seconds, 1))


def _claude(prompt: str, workdir: Path, raw_file: str, max_turns: int = 60, timeout_s: int = 1200) -> tuple[str, dict]:
    """One `claude -p` run with Opus: Read for the photos, WebSearch and WebFetch for prices and
    specifications; no Bash or writes. Returns the reply text and the envelope."""
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}  # use the Claude Code login
    proc = subprocess.run(
        ["claude", "-p", "--model", "claude-opus-5-5", "--output-format", "json",
         "--allowedTools", "Read,WebSearch,WebFetch", "--disallowedTools", "Bash,Edit,Write,NotebookEdit",
         "--max-turns", str(max_turns), prompt],
        cwd=workdir, env=env, capture_output=True, text=True, timeout=timeout_s,
    )
    (workdir / raw_file).write_text(proc.stdout or proc.stderr)
    envelope = json.loads(proc.stdout)
    if envelope.get("is_error"):
        raise RuntimeError(f"claude -p failed: {envelope.get('result')}")
    return envelope["result"], envelope


def run_opus(photos: list[tuple[Path, str]], city: str, workdir: Path, timeout_s: int = 1200) -> SourceResult:
    prompt = PROMPT.format(city=city, photo_list=_photo_list(photos), categories=", ".join(CATEGORIES),
                           genres=", ".join(GENRES))
    t0 = time.time()
    text, envelope = _claude(prompt, workdir, "opus_raw.json", timeout_s=timeout_s)
    result = _to_result(_parse(text), "opus", time.time() - t0)
    result.notes.append(f"claude -p reported cost ${envelope.get('total_cost_usd', 0):.2f}, "
                        f"{envelope.get('num_turns')} turns")
    return result


def run_astra(photos: list[tuple[Path, str]], city: str, workdir: Path, timeout_s: int = 1200) -> SourceResult:
    key = os.environ["OPENAI_API_KEY"]
    prompt = PROMPT.format(city=city, photo_list=_photo_list(photos), categories=", ".join(CATEGORIES),
                           genres=", ".join(GENRES)).replace("with the Read tool", "attached below")
    content = [{"type": "input_text", "text": prompt}]
    for p, tag in photos:
        b64 = base64.b64encode(p.read_bytes()).decode()
        content.append({"type": "input_text", "text": f"{p.name} (tag: {tag})"})
        content.append({"type": "input_image", "image_url": f"data:image/jpeg;base64,{b64}"})
    t0 = time.time()
    r = httpx.post("https://api.openai.com/v1/responses", timeout=timeout_s,
                   headers={"Authorization": f"Bearer {key}"},
                   json={"model": "gpt-6-astra", "input": [{"role": "user", "content": content}],
                         "tools": [{"type": "web_search"}]})
    (workdir / "astra_raw.json").write_text(r.text)
    r.raise_for_status()
    body = r.json()
    text = "".join(c.get("text", "") for o in body.get("output", []) if o.get("type") == "message"
                   for c in o.get("content", []))
    return _to_result(_parse(text), "astra", time.time() - t0)


def run(backend: str, photos: list[tuple[Path, str]], city: str, workdir: Path) -> SourceResult:
    return {"opus": run_opus, "astra": run_astra}[backend](photos, city, workdir)


OBJECT_PROMPT = """You are identifying and pricing ONE object in a room in {city}, India, for a home insurance claim.
The owner's item list calls it "{name}" (category {category}).{note}
Every photo of this object (read each one with the Read tool):
{photo_list}

1. Identify it as exactly as the photos allow: brand, model number, variant. Read every label, sticker,
   rating plate and screen. Laptops, desktops, phones and tablets: the CPU, GPU, RAM and storage, from any
   label, the box or a screen showing system information, or from the official specification of a model
   number you read. Never guess what you cannot read or look up; say what is uncertain.
2. Dimensions: search the web for this product's dimensions (width x height x depth, cm) from the
   manufacturer or a retailer's specification. If the exact model is unknown, the closest equivalent's,
   and say so. Also estimate its size from the photos.
3. Price: search the web for what it costs to buy this object NEW in {city} or elsewhere in India today
   (Amazon.in, Flipkart, Croma, Reliance Digital, the brand's site, local retailers). Price like kind and
   quality: the same type, size and grade. price_kind is "exact" when you priced this exact model,
   "closest" for the nearest equivalent (say what and why in price_note), "estimate" when no page gave a
   price (then price_source is "estimate"). A used or refurbished listing is not a price.

Reply with ONLY a JSON object, no prose, no code fence:
{{"category": "{category}", "name": "", "brand": null, "model": null, "attributes": {{}}, "quantity": 1,
  "condition": "good", "evidence": "text you read on it", "dimensions_cm": {{"width": 0, "height": 0, "depth": 0}},
  "dimensions_source": "URL or 'estimate from the photos'", "seen_size_cm": {{"width": 0, "height": 0}},
  "rcv_inr": 0, "price_kind": "exact", "price_source": "", "price_note": ""}}
"""
OBJECT_WORKERS = 4  # parallel claude -p runs
OBJECT_MAX_PHOTOS = 6  # per object: the close-ups, then crops of the largest detections


def object_photos(entry: dict, closeups: list[Path], photo_dir: Path, out: Path) -> list[tuple[Path, str]]:
    """Every photo of one listed item: its close-ups, then crops of where it was detected (the
    largest boxes first, each crop with some of the room around it)."""
    from PIL import Image

    shots = [(p, "close-up the owner took of it") for p in closeups]
    regions = sorted((entry.get("detected") or {}).get("regions") or [],
                     key=lambda r: -(r["box"][2] - r["box"][0]) * (r["box"][3] - r["box"][1]))
    seen = set()
    for r in regions:
        if len(shots) >= OBJECT_MAX_PHOTOS or r["photo"] in seen or not (photo_dir / r["photo"]).exists():
            continue
        seen.add(r["photo"])
        im = Image.open(photo_dir / r["photo"]).convert("RGB")
        w, h = im.size
        x0, y0, x1, y1 = r["box"]
        mx, my = 0.25 * (x1 - x0), 0.25 * (y1 - y0)
        crop = im.crop((int(max(0, x0 - mx) * w), int(max(0, y0 - my) * h), int(min(1, x1 + mx) * w), int(min(1, y1 + my) * h)))
        crop.thumbnail((1280, 1280))
        dst = out / f"{entry['id']}_{len(shots):02d}.jpg"
        dst.parent.mkdir(parents=True, exist_ok=True)
        crop.save(dst, quality=90)
        shots.append((dst, f"crop around it in the room photo {r['photo']}"))
    return shots[:OBJECT_MAX_PHOTOS]


def run_objects(entries: list[dict], closeups: dict[str, list[Path]], photo_dir: Path, city: str,
                workdir: Path, progress=None) -> SourceResult:
    """Pipeline 2, second pass: one Opus run per listed object, with every photo of it at once,
    for its identity, its dimensions from the web and its local price. Each result is tied to its
    item (Item.link), like an owner note, so Jev sees it as a fourth reading of that object."""
    from concurrent.futures import ThreadPoolExecutor

    say = progress or (lambda **kw: None)
    t0 = time.time()
    todo = []
    for e in entries:
        if e["category"] == "book":  # spines are read by pipeline 1 and the room pass
            continue
        shots = object_photos(e, closeups.get(e["id"], []), photo_dir, workdir / "objects")
        if shots:
            todo.append((e, shots))
    cost, notes = 0.0, []

    def one(job):
        e, shots = job
        note = f"\nThe owner's note on it: \"{e['note']}\"." if e.get("note") else ""
        prompt = OBJECT_PROMPT.format(city=city, name=e["name"], category=e["category"], note=note,
                                      photo_list=_photo_list(shots))
        saved = workdir / "objects" / f"{e['id']}.json"  # the same prompt and photos: the answer is reused
        if saved.exists() and json.loads(saved.read_text()).get("prompt") == prompt:
            s = json.loads(saved.read_text())
            return e, shots, s["answer"], {"total_cost_usd": 0, "reused": True}
        text, env = _claude(prompt, workdir, f"objects/{e['id']}_raw.json", max_turns=30, timeout_s=900)
        answer = _parse(text)
        saved.write_text(json.dumps({"prompt": prompt, "answer": answer, "cost_usd": env.get("total_cost_usd")}, indent=1))
        return e, shots, answer, env

    items = []
    with ThreadPoolExecutor(OBJECT_WORKERS) as pool:
        for k, fut in enumerate([pool.submit(one, job) for job in todo]):
            say(step="Opus, one object at a time", done=k, total=len(todo))
            try:
                e, shots, raw, env = fut.result()
            except Exception as ex:  # one object failing leaves the others
                notes.append(f"{todo[k][0]['name']}: {type(ex).__name__}")
                continue
            cost += env.get("total_cost_usd") or 0
            item = _to_result({"items": [raw]}, "object", 0).items[0]
            dims = raw.get("dimensions_cm") or {}
            if dims.get("width") and dims.get("height"):
                item.product_size = " x ".join(f"{float(dims[k]):g}" for k in ("width", "height", "depth") if dims.get(k)) + " cm"
                item.attributes["dimensions_source"] = str(raw.get("dimensions_source") or "")
            item.id, item.link = f"object-{e['id']}", e["id"]
            item.photos = [p.name for p, _ in shots]
            items.append(item)
    notes.insert(0, f"{len(items)} of {len(todo)} listed objects, one claude -p run each with all their photos; "
                    f"reported cost ${cost:.2f}")
    return SourceResult(source="object", items=items, notes=notes, seconds=round(time.time() - t0, 1))
