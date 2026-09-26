"""Merge several captures of one room into one, as if it had been taken in a single session.

    uv run python scripts/merge_captures.py <capture> <capture> ... [--closeup CATEGORY:NAME=PATH ...]

1. A new capture: every room photo and the video of the inputs, and the first capture's
   room details.
2. Detection runs once over all photos and video frames together.
3. Every close-up, voice note and typed note of the old captures moves to the matching new
   item. Detected items match by box overlap in the same photo or frame (the photos and frames
   are the same files). Items the owner added match by category and name. Anything without a
   match is kept as an added item. Several notes on one item are all kept and read together.
4. --closeup attaches an extra photo to the new item of that category whose name matches best.
"""

import argparse
import json
import secrets
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from room_valuation import run, session  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MEDIA = set(run.PHOTO) | set(run.AUDIO)


def _contain(a, b) -> float:
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    small = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))
    return ix * iy / small if small > 0 else 0.0


def _regions(entry: dict) -> list[dict]:
    return (entry.get("detected") or {}).get("regions") or []


SYNONYMS = {"desk": "table", "almirah": "wardrobe", "cupboard": "wardrobe", "almera": "wardrobe", "tv": "television",
            "notebook": "laptop", "ac": "conditioner", "cot": "bed"}


def _words(name: str) -> set[str]:
    import re

    return {SYNONYMS.get(w, w) for w in re.findall(r"[a-z]+", name.lower()) if len(w) >= 2}


def word_sim(a: str, b: str) -> float:
    """Shared words over the smaller name, with a few synonyms (desk = table). Letter-level
    similarity matched 'chair' to 'curtain'."""
    wa, wb = _words(a), _words(b)
    return len(wa & wb) / min(len(wa), len(wb)) if wa and wb else 0.0


def _name_match(entry: dict, candidates: list[dict]) -> dict | None:
    same = [c for c in candidates if c["category"] == entry["category"] and c["state"] != "removed"]
    scored = [(word_sim(entry["name"], c["name"]), c) for c in same]
    scored = [(s, c) for s, c in scored if s > 0]
    return max(scored, key=lambda sc: sc[0])[1] if scored else None


def match(old: dict, new_items: list[dict]) -> tuple[dict | None, str]:
    """The new item an old one becomes, and why."""
    regs = _regions(old)
    best, score = None, 0.0
    for n in new_items:
        for ro in regs:
            for rn in _regions(n):
                if ro["photo"] == rn["photo"]:
                    # overlap first, but a keyboard box inside the laptop box is not the laptop
                    s = (_contain(ro["box"], rn["box"]) + (0.25 if n["category"] == old["category"] else 0)
                         + 0.5 * word_sim(old["name"], n["name"]))
                    if s > score:
                        best, score = n, s
    if best is not None and score >= 0.6:
        return best, f"box overlap {score:.2f} in the same photo"
    n = _name_match(old, new_items)
    return (n, "same category and name") if n else (None, "no match")


def _copy_media(src: Path, dst: Path) -> list[str]:
    dst.mkdir(parents=True, exist_ok=True)
    moved = []
    for f in sorted(src.glob("*")):
        if f.suffix.lower() not in MEDIA:
            continue
        kind = "voice" if f.suffix.lower() in run.AUDIO else "closeup"
        n = len(list(dst.glob(f"{kind}*")))
        target = dst / f"{kind}_{n:02d}{f.suffix.lower()}"
        shutil.copy(f, target)
        moved.append(f"{src.parent.parent.name}/{src.name}/{f.name} -> {target.name}")
    return moved


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("captures", nargs="+")
    ap.add_argument("--closeup", action="append", default=[], help="CATEGORY:NAME=PATH")
    ap.add_argument("--into", help="an earlier merge: keep its detection, redo only the carrying")
    args = ap.parse_args()
    sources = [Path(c) for c in args.captures]
    if args.into:
        cap = Path(args.into)
        carry(cap, session.load(cap), sources, args.closeup)
        return
    cap, data = build(sources)
    carry(cap, data, sources, args.closeup)


def build(sources: list[Path]) -> tuple[Path, dict]:
    """A new capture with every room photo and the video, then detection over all of it."""
    cid = time.strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(3)
    cap = ROOT / "data" / "captures" / cid
    (cap / "photos" / "room").mkdir(parents=True)
    meta = json.loads((sources[0] / "meta.json").read_text())
    for s in sources:  # tape dimensions from whichever capture has them
        m = json.loads((s / "meta.json").read_text())
        if m.get("length_cm") and m.get("width_cm"):
            meta.update(length_cm=m["length_cm"], width_cm=m["width_cm"])
    meta["merged_from"] = [s.name for s in sources]
    (cap / "meta.json").write_text(json.dumps(meta, indent=1))
    video_done = False
    for s in sources:
        for p in sorted((s / "photos" / "room").glob("*")):
            shutil.copy(p, cap / "photos" / "room" / p.name)  # same names keep the old boxes comparable
        v = run._first(s, "video", run.VIDEO + (".webm",))
        if v and not video_done:
            shutil.copy(v, cap / f"video{v.suffix}")
            video_done = True
    session.save(cap, {"stage": "queued", "items": [], "meta": meta})
    print(f"merged capture {cid}: {len(list((cap / 'photos' / 'room').glob('*')))} room photos, video: {video_done}")

    data = run.detect(cap)
    return cap, data


def carry(cap: Path, data: dict, sources: list[Path], closeups: list[str]) -> None:
    """Move media, notes and review decisions from the old captures onto the new items."""
    data["items"] = [e for e in data["items"] if e["state"] != "added"]
    for e in data["items"]:  # back to what detection said, so the carrying can be redone
        det = e.get("detected") or {}
        e.update(state="detected", note="", name=det.get("name", e["name"]), quantity=det.get("quantity") or 1)
    shutil.rmtree(cap / "items", ignore_errors=True)
    new_items = list(data["items"])
    print(f"detection: {len(new_items)} items")

    report, added = [], 0
    # the owner's removals first: a detector duplicate removed in either review is removed here
    for s in sources:
        for e in session.load(s)["items"]:
            if e["state"] == "removed" and _regions(e):
                target, why = match(e, [n for n in new_items if n["state"] == "detected"])
                if target is not None and why.startswith("box"):
                    target["state"] = "removed"
                    report.append({"from": f"{s.name}/{e['id']} ({e['name']})", "to": f"{target['id']} ({target['name']})",
                                   "why": f"removed by the owner ({why})", "media": []})
    for s in sources:
        old = session.load(s)
        for e in old["items"]:
            if e["state"] == "removed":
                continue
            media = s / "items" / e["id"]
            has_media = media.is_dir() and any(f.suffix.lower() in MEDIA for f in media.glob("*"))
            if not has_media and not e.get("note") and e["state"] != "added":
                continue
            # an item the owner kept and wrote a note on wins over a removal of the same item in
            # the other review: restore it rather than attach the note to its neighbour
            target, why = match(e, new_items)
            if target is not None and target["state"] == "removed":
                if why.startswith("box") and word_sim(e["name"], target["name"]) > 0:
                    target["state"] = "detected"
                    why = f"{why}; restored, it has the owner's notes"
                else:
                    target, why = match(e, [n for n in new_items if n["state"] != "removed"])
            if target is None:
                added += 1
                target = {**e, "id": f"added-{added}", "state": "added", "detected": None}
                data["items"].append(target)
                new_items.append(target)
                why = "kept as an added item"
            moved = _copy_media(media, cap / "items" / target["id"]) if has_media else []
            if e.get("note"):
                target["note"] = ". ".join(x for x in (target.get("note"), e["note"]) if x)
            if e["state"] == "added" and target["state"] != "added":
                target["name"] = e["name"]  # the owner's name for it is more specific than the detector's
            report.append({"from": f"{s.name}/{e['id']} ({e['name']})", "to": f"{target['id']} ({target['name']})",
                           "why": why, "media": moved, "note": e.get("note") or None})
    for spec in closeups:
        head, _, path = spec.partition("=")
        cat, _, name = head.partition(":")
        target = _name_match({"category": cat, "name": name}, new_items)
        if target is None:
            added += 1
            target = {"id": f"added-{added}", "state": "added", "category": cat, "name": name, "brand": None,
                      "model": None, "quantity": 1, "thumb": None, "closeups": [], "voice": None, "note": ""}
            data["items"].append(target)
        d = cap / "items" / target["id"]
        d.mkdir(parents=True, exist_ok=True)
        dst = d / f"closeup_{len(list(d.glob('closeup*'))):02d}{Path(path).suffix.lower()}"
        shutil.copy(path, dst)
        report.append({"from": path, "to": f"{target['id']} ({target['name']})", "why": "extra close-up", "media": [dst.name]})
    session.update(cap, lambda d: d.update(items=data["items"], stage="review", merge_report=report))
    print(json.dumps(report, indent=1))
    print(f"review page: /c/{cap.name}")


if __name__ == "__main__":
    main()
