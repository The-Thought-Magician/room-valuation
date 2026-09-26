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


def run(audio: Path, workdir: Path) -> SourceResult:
    t0 = time.time()
    segments = models.transcribe(str(audio))
    text = " ".join(s["text"] for s in segments)
    (workdir / "transcript.json").write_text(json.dumps(segments, indent=1))
    items = extract(text) if text.strip() else []
    return SourceResult(source="voice", items=items, seconds=round(time.time() - t0, 1),
                        notes=[f"transcript: {text[:500]}"])
