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
        items.append(Item(
            id=f"{source}-{i}", source=source, category=cat, name=raw.get("name") or cat,
            brand=raw.get("brand"), model=raw.get("model"),
            attributes={str(k): str(v) for k, v in (raw.get("attributes") or {}).items()},
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


def run_opus(photos: list[tuple[Path, str]], city: str, workdir: Path, timeout_s: int = 1200) -> SourceResult:
    prompt = PROMPT.format(city=city, photo_list=_photo_list(photos), categories=", ".join(CATEGORIES),
                           genres=", ".join(GENRES))
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}  # use the Claude Code login
    t0 = time.time()
    proc = subprocess.run(
        ["claude", "-p", "--model", "claude-opus-5-5", "--output-format", "json",
         "--allowedTools", "Read,WebSearch,WebFetch", "--disallowedTools", "Bash,Edit,Write,NotebookEdit",
         "--max-turns", "60", prompt],
        cwd=workdir, env=env, capture_output=True, text=True, timeout=timeout_s,
    )
    (workdir / "opus_raw.json").write_text(proc.stdout or proc.stderr)
    envelope = json.loads(proc.stdout)
    if envelope.get("is_error"):
        raise RuntimeError(f"claude -p failed: {envelope.get('result')}")
    result = _to_result(_parse(envelope["result"]), "opus", time.time() - t0)
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
