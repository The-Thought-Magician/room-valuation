"""Third input: the owner's spoken narration. Whisper transcribes it; the local model turns
each mentioned object into an item with what the owner said (brand, size, price paid, age)."""

import json
import re
import time
from pathlib import Path

from room_valuation import models
from room_valuation.schema import CATEGORIES, Item, SourceResult

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
        paid = _num(d.get("price_paid_inr"))
        items.append(Item(id=f"voice-{i}", source="voice", category=cat, name=d.get("name") or cat,
                          brand=d.get("brand"), model=d.get("model"), attributes=attrs, evidence=d.get("quote"),
                          price_paid_inr=paid, age_years=_num(d.get("age_years")),
                          rcv_inr=paid, price_source="said by owner" if paid else None))
    return items


def run(audio: Path, workdir: Path) -> SourceResult:
    t0 = time.time()
    segments = models.transcribe(str(audio))
    text = " ".join(s["text"] for s in segments)
    (workdir / "transcript.json").write_text(json.dumps(segments, indent=1))
    items = extract(text) if text.strip() else []
    return SourceResult(source="voice", items=items, seconds=round(time.time() - t0, 1),
                        notes=[f"transcript: {text[:500]}"])
