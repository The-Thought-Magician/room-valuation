"""A capture session: room photos, then the detected item list the owner reviews, then per-item
close-ups and voice notes, then the valuation. State lives in <capture>/session.json.

Item states: detected (from the room photos), added (the owner added something the detector
missed), removed (the owner said it is not an item or a duplicate)."""

import json
import threading
from pathlib import Path

from PIL import Image

from room_valuation.schema import Item

LOCK = threading.Lock()
# walk-through order: likely value first, cheap soft goods last
PRIORITY = ["laptop", "monitor", "appliance", "phone", "furniture", "book", "audio", "computer_accessory",
            "networking", "lighting", "electrical_fixture", "building_fixture", "decor", "bedding", "kitchenware",
            "bag_clothing", "other"]


def path(capture: Path) -> Path:
    return capture / "session.json"


def load(capture: Path) -> dict:
    f = path(capture)
    return json.loads(f.read_text()) if f.exists() else {"stage": "new", "items": []}


def save(capture: Path, data: dict) -> None:
    with LOCK:
        tmp = path(capture).with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=1, default=str))
        tmp.replace(path(capture))


def update(capture: Path, fn) -> dict:
    with LOCK:
        data = load(capture)
        fn(data)
        tmp = path(capture).with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=1, default=str))
        tmp.replace(path(capture))
    return data


def crop_thumbnail(photo: Path, box: list[float], dst: Path, margin: float = 0.08) -> None:
    im = Image.open(photo).convert("RGB")
    w, h = im.size
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    c = im.crop((int(max(0, x0 - margin * bw) * w), int(max(0, y0 - margin * bh) * h),
                 int(min(1, x1 + margin * bw) * w), int(min(1, y1 + margin * bh) * h)))
    c.thumbnail((480, 480))
    dst.parent.mkdir(parents=True, exist_ok=True)
    c.save(dst, quality=85)


def from_detection(items: list[Item], photo_dir: Path, thumbs: Path) -> list[dict]:
    """Session entries for the review list, sorted by walk-through priority."""
    out = []
    for it in items:
        thumb = None
        if it.regions:
            r = max(it.regions, key=lambda r: (r["box"][2] - r["box"][0]) * (r["box"][3] - r["box"][1]))
            thumb = f"{it.id}.jpg"
            crop_thumbnail(photo_dir / r["photo"], r["box"], thumbs / thumb)
        out.append({"id": it.id, "state": "detected", "category": it.category, "name": it.name,
                    "brand": it.brand, "model": it.model, "quantity": it.quantity, "thumb": thumb,
                    "closeups": [], "voice": None, "note": "", "detected": it.model_dump()})
    rank = {c: i for i, c in enumerate(PRIORITY)}
    out.sort(key=lambda e: (rank.get(e["category"], 99), e["name"]))
    return out


def active(data: dict) -> list[dict]:
    return [e for e in data["items"] if e["state"] != "removed"]
