"""Third input: the owner's spoken narration. Whisper transcribes it; the local model turns
each mentioned object into an item with what the owner said (brand, size, price paid, age)."""

import json
import re
import time
from pathlib import Path

from room_valuation import models
from room_valuation.schema import CATEGORIES, Item, SourceResult

RECENT_YEARS = 2  # a price paid is a replacement cost only when the purchase is this recent

EXTRACT = (
    "Below is what a person said while walking through their room for an insurance inventory. "
    "List every physical object they mention. Reply with a JSON array only, no prose. Each element: "
    '{{"category": one of [{categories}], "name": "short name", "brand": null or string, "model": null or string, '
    '"size": null or string, "price_paid_inr": null or number in rupees (1.9 lakh = 190000, 16.5k = 16500), '
    '"age_years": null or number (bought last year = 1), "quote": "the words they used"}}.\n\nTranscript:\n{text}'
)


def _array(text: str) -> list[dict]:
    m = re.search(r"\[.*\]", text, re.S)
    if not m:
        return []
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []
    return [d for d in data if isinstance(d, dict)]


def _num(v) -> float | None:
    try:
        return float(v) if v not in (None, "", "null") else None
    except (TypeError, ValueError):
        return None


def extract(transcript: str) -> list[Item]:
    vlm = models.VLM()
    raw = _array(vlm.ask(EXTRACT.format(categories=", ".join(CATEGORIES), text=transcript), max_new_tokens=900))
    del vlm
    models.free()
    items = []
    for i, d in enumerate(raw):
        cat = d.get("category") if d.get("category") in CATEGORIES else "other"
        attrs = {"size": str(d["size"])} if d.get("size") else {}
        paid, age = _num(d.get("price_paid_inr")), _num(d.get("age_years"))
        # what someone paid 35 years ago says nothing about today's replacement cost; it stays
        # on the item as evidence, and the age still drives depreciation
        recent = paid is not None and (age is None or age <= RECENT_YEARS)
        items.append(Item(id=f"voice-{i}", source="voice", category=cat, name=d.get("name") or cat,
                          brand=d.get("brand"), model=d.get("model"), attributes=attrs, evidence=d.get("quote"),
                          price_paid_inr=paid, age_years=age,
                          rcv_inr=paid if recent else None, price_source="said by owner" if recent else None,
                          price_note=None if recent or paid is None else
                          f"paid Rs {paid:,.0f} about {age:g} years ago; too old to be a replacement price"))
    return items


ITEM_NOTE = (
    "The owner recorded a voice note about one object in their room, a {name} ({category}). "
    "Reply with one JSON object and nothing else, with keys: brand, model, size, "
    "price_paid_inr (number in rupees; 1.9 lakh = 190000, 16.5k = 16500), age_years (number; bought last "
    "year = 1), quantity (number), condition (like_new, good, fair or poor), facts (anything else they said). "
    "Use null for anything they did not say.\n\nTranscript: {text}"
)


def _item_claim(d: dict, entry: dict, text: str) -> Item:
    paid, age = _num(d.get("price_paid_inr")), _num(d.get("age_years"))
    recent = paid is not None and (age is None or age <= RECENT_YEARS)
    attrs = {k: str(d[k]) for k in ("size", "facts") if d.get(k) not in (None, "", "null")}
    brand = d.get("brand") if d.get("brand") not in (None, "", "null") else None
    model = d.get("model") if d.get("model") not in (None, "", "null") else None
    name = " ".join(x for x in (brand, model) if x) or entry["name"]
    return Item(id=f"voice-{entry['id']}", source="voice", category=entry["category"], name=name, brand=brand,
                model=model, attributes=attrs, quantity=int(_num(d.get("quantity")) or entry.get("quantity") or 1),
                condition=d.get("condition") if d.get("condition") in ("like_new", "good", "fair", "poor") else None,
                evidence=text, price_paid_inr=paid, age_years=age, link=entry["id"],
                rcv_inr=paid if recent else None, price_source="said by owner" if recent else None,
                price_note=None if recent or paid is None else
                f"paid Rs {paid:,.0f} about {age:g} years ago; too old to be a replacement price")


def run_items(notes: list[tuple[dict, Path]], room_note: Path | None, workdir: Path, progress=None) -> SourceResult:
    """One voice note per item page, plus an optional room-level narration."""
    t0 = time.time()
    say = progress or (lambda **kw: None)
    paths = [str(p) for _, p in notes] + ([str(room_note)] if room_note else [])
    if not paths:
        return SourceResult(source="voice", items=[], seconds=0.0, notes=["no voice notes"])
    say(step="transcribing voice notes", done=0, total=len(paths))
    segments = models.transcribe(paths)
    (workdir / "transcripts.json").write_text(json.dumps(segments, indent=1))
    texts = {p: " ".join(s["text"] for s in segs).strip() for p, segs in segments.items()}
    items = []
    vlm = models.VLM()
    for k, (entry, p) in enumerate(notes):
        say(step="reading voice notes", done=k, total=len(notes))
        text = texts.get(str(p), "")
        if not text:
            continue
        raw = vlm.ask(ITEM_NOTE.format(name=entry["name"], category=entry["category"], text=text), max_new_tokens=220)
        m = re.search(r"\{.*\}", raw, re.S)
        try:
            d = json.loads(m.group(0)) if m else {}
        except json.JSONDecodeError:
            d = {}
        items.append(_item_claim(d if isinstance(d, dict) else {}, entry, text))
    del vlm
    models.free()
    if room_note and texts.get(str(room_note)):
        items += [it.model_copy(update={"id": f"voice-room-{i}"}) for i, it in enumerate(extract(texts[str(room_note)]))]
    return SourceResult(source="voice", items=items, seconds=round(time.time() - t0, 1),
                        notes=[f"{len(notes)} item notes" + (", one room narration" if room_note else "")])


def run(audio: Path, workdir: Path) -> SourceResult:
    t0 = time.time()
    segments = models.transcribe([str(audio)])[str(audio)]
    text = " ".join(s["text"] for s in segments)
    (workdir / "transcript.json").write_text(json.dumps(segments, indent=1))
    items = extract(text) if text.strip() else []
    return SourceResult(source="voice", items=items, seconds=round(time.time() - t0, 1),
                        notes=[f"transcript: {text[:500]}"])
