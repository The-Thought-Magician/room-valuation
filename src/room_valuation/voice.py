"""Third input: the owner's spoken narration. Whisper transcribes it; the local model turns
each mentioned object into an item with what the owner said (brand, size, price paid, age)."""

import json
import re
import time
from pathlib import Path

from room_valuation import models
from room_valuation.schema import CATEGORIES, Item, SourceResult

RECENT_YEARS = 2  # a price paid is a replacement cost only when the purchase is this recent

# Prices and ages are read with rules, not by the 2B model: on the first real capture it
# invented a Rs 12,000 charger and turned "40 years back" into one year (2026-09-26).
NUM_WORDS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
             "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20,
             "thirty": 30, "forty": 40, "fifty": 50, "half": 0.5}
_NUM = r"(\d+(?:\.\d+)?|" + "|".join(NUM_WORDS) + r")"
MULT = {"k": 1e3, "thousand": 1e3, "l": 1e5, "lakh": 1e5, "lakhs": 1e5, "lac": 1e5, "lacs": 1e5, "crore": 1e7}
FREE = re.compile(r"\b(for free|came free|free of cost|was free|got it free|provided by|company provided|"
                  r"came with (?:my|the)|given by|gift(?:ed)?)\b", re.I)


def _n(s: str) -> float:
    s = s.lower()
    return float(NUM_WORDS[s]) if s in NUM_WORDS else float(s)


def parse_price(text: str) -> float | None:
    """Rupee amount said out loud: '16K', '1.9 lakhs', 'Rs. 2500', '500 rupees', '5.5k'."""
    t = text.lower().replace(",", "")
    m = re.search(_NUM + r"\s*(k|thousand|lakhs?|lacs?|l|crore)\b", t)
    if m:
        return _n(m.group(1)) * MULT[m.group(2)]
    m = re.search(r"(?:rs\.?|inr|₹)\s*(\d+(?:\.\d+)?)", t) or re.search(r"(\d+(?:\.\d+)?)\s*(?:rupees|rs\b|inr)", t)
    return float(m.group(1)) if m else None


def parse_age(text: str) -> float | None:
    """Age in years: '3 years back', 'one month old', 'last year', '40 years ago', 'brand new'."""
    t = text.lower()
    m = re.search(_NUM + r"\s*(years?|yrs?)\s*(back|ago|old|before)", t) or re.search(
        r"(?:bought|purchased|made|got)\s+(?:it\s+)?" + _NUM + r"\s*(years?|yrs?)", t)
    if m:
        return _n(m.group(1))
    m = re.search(_NUM + r"\s*months?\s*(back|ago|old|before)", t)
    if m:
        return round(_n(m.group(1)) / 12, 2)
    if re.search(r"\blast year\b", t):
        return 1.0
    if re.search(r"\b(this year|brand new|just bought|few days|last week|this month)\b", t):
        return 0.0
    return None

EXTRACT = (
    "Below is what a person said while walking through their room for an insurance inventory. "
    "List every physical object they mention. Reply with a JSON array only, no prose. Each element: "
    '{{"category": one of [{categories}], "name": "short name", "brand": null or string, "model": null or string, '
    '"size": null or string, "price_paid_inr": null or number in rupees (2.4 lakh = 240000, 12k = 12000), '
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
    "Reply with one JSON object and nothing else, with keys: brand, model, size, quantity (number), "
    "condition (like_new, good, fair or poor), facts (anything else they said, short). "
    "Use null for anything they did not say. Do not guess.\n\nTranscript: {text}"
)


def _item_claim(d: dict, entry: dict, text: str) -> Item:
    """Brand and model from the model's reading; price, age and 'it was free' from rules."""
    paid, age = parse_price(text), parse_age(text)
    free = bool(FREE.search(text))
    if free and paid == 0:
        paid = None
    recent = bool(paid) and not free and (age is None or age <= RECENT_YEARS)
    attrs = {k: str(d[k]) for k in ("size", "facts") if d.get(k) not in (None, "", "null")}
    if free:
        attrs["acquired"] = "free or provided (the owner said so); may not be the owner's to claim"
    brand = d.get("brand") if d.get("brand") not in (None, "", "null") else None
    model = d.get("model") if d.get("model") not in (None, "", "null") else None
    name = " ".join(x for x in (brand, model) if x) or entry["name"]
    note = None
    if paid and not recent:
        note = (f"paid Rs {paid:,.0f} about {age:g} years ago; too old to be a replacement price" if age is not None
                else f"paid Rs {paid:,.0f}")
    return Item(id=f"voice-{entry['id']}", source="voice", category=entry["category"], name=name, brand=brand,
                model=model, attributes=attrs, quantity=int(_num(d.get("quantity")) or entry.get("quantity") or 1),
                condition=d.get("condition") if d.get("condition") in ("like_new", "good", "fair", "poor") else None,
                evidence=text, price_paid_inr=paid, age_years=age, link=entry["id"],
                rcv_inr=paid if recent else None, price_source="said by owner" if recent else None, price_note=note)


def _claim_from(vlm, entry: dict, text: str) -> Item:
    prompt = ITEM_NOTE.format(name=entry["name"], category=entry["category"], text=text)
    raw = vlm.ask(prompt, max_new_tokens=220) if vlm else "{}"
    m = re.search(r"\{.*\}", raw, re.S)
    try:
        d = json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        d = {}
    return _item_claim(d if isinstance(d, dict) else {}, entry, text)


def run_items(notes: list[tuple[dict, list[Path]]], room_note: Path | None, workdir: Path, progress=None,
              reuse_transcripts: bool = False, entries: list[dict] | None = None) -> SourceResult:
    """What the owner said and typed about each item, read as one statement per item: every
    voice note on the item plus its typed note. Plus an optional room-level narration."""
    t0 = time.time()
    say = progress or (lambda **kw: None)
    paths = [str(p) for _, ps in notes for p in ps] + ([str(room_note)] if room_note else [])
    saved = workdir / "transcripts.json"
    segments: dict = {}
    if paths:
        if reuse_transcripts and saved.exists() and all(p in json.loads(saved.read_text()) for p in paths):
            segments = json.loads(saved.read_text())
        else:
            say(step="transcribing voice notes", done=0, total=len(paths))
            segments = models.transcribe(paths)
            saved.write_text(json.dumps(segments, indent=1))
    texts = {p: " ".join(s["text"] for s in segs).strip() for p, segs in segments.items()}
    said = {e["id"]: " ".join(texts.get(str(p), "") for p in ps).strip() for e, ps in notes}
    by_id = {e["id"]: e for e, _ in notes} | {e["id"]: e for e in entries or [] if e.get("note")}
    statements = {}
    for iid, e in by_id.items():
        parts = [said.get(iid, ""), (e.get("note") or "").strip()]
        text = ". ".join(x.rstrip(".") for x in parts if x)
        if text:
            statements[iid] = text
    items = []
    vlm = models.VLM() if any(said.values()) else None  # typed notes alone need no model
    for k, (iid, text) in enumerate(statements.items()):
        say(step="reading notes", done=k, total=len(statements))
        items.append(_claim_from(vlm if said.get(iid) else None, by_id[iid], text))
    if vlm:
        del vlm
        models.free()
    if room_note and texts.get(str(room_note)):
        items += [it.model_copy(update={"id": f"voice-room-{i}"}) for i, it in enumerate(extract(texts[str(room_note)]))]
    n_voice = sum(len(ps) for _, ps in notes)
    n_typed = sum(1 for e in entries or [] if e.get("note"))
    return SourceResult(source="voice", items=items, seconds=round(time.time() - t0, 1),
                        notes=[f"{n_voice} voice notes and {n_typed} typed notes on {len(statements)} items"
                               + (", one room narration" if room_note else "")])


def run(audio: Path, workdir: Path) -> SourceResult:
    t0 = time.time()
    segments = models.transcribe([str(audio)])[str(audio)]
    text = " ".join(s["text"] for s in segments)
    (workdir / "transcript.json").write_text(json.dumps(segments, indent=1))
    items = extract(text) if text.strip() else []
    return SourceResult(source="voice", items=items, seconds=round(time.time() - t0, 1),
                        notes=[f"transcript: {text[:500]}"])
