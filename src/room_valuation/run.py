"""A capture goes through two jobs.

detect(capture): room photos -> the item list the owner reviews (session.json, stage "review")
value(capture):  reviewed items + per-item close-ups and voice notes -> the valuation report

Capture folder layout (what the capture pages upload):
    meta.json                  {"room": "bedroom", "city": "Rourkela", "length_cm": null, "width_cm": null}
    photos/room/*.jpg          photos covering the room
    items/<item id>/*.jpg      close-ups taken on that item's page (labels, stickers, spines)
    items/<item id>/voice.*    the owner's voice note about that item
    voice.*                    optional room-level narration
    video.*                    optional walkthrough, used only for floor area
"""

import json
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageOps

from room_valuation import area, frontier, jev, local, session, valuation, voice
from room_valuation.schema import SourceResult

BACKEND_NAMES = {"opus": "claude-opus-5-5", "astra": "gpt-6-astra", "none": "skipped (test run)"}
AUDIO = (".webm", ".m4a", ".mp3", ".wav", ".ogg", ".aac")
VIDEO = (".mp4", ".mov", ".mkv")
PHOTO = (".jpg", ".jpeg", ".png", ".webp")


def _status(workdir: Path, stage: str, state: str, **extra):
    f = workdir / "status.json"
    s = json.loads(f.read_text()) if f.exists() else {"stages": {}}
    s["stages"][stage] = {"state": state, "t": round(time.time(), 1), **extra}
    s["current"] = stage
    f.write_text(json.dumps(s, indent=1))


def _normalize(src: Path, dst: Path) -> Path:
    """EXIF-upright, at most 2048 px on the long side, JPEG. Phones store rotation in EXIF."""
    im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    im.thumbnail((2048, 2048))
    dst.parent.mkdir(parents=True, exist_ok=True)
    im.save(dst, quality=90)
    return dst


def room_photos(capture: Path, workdir: Path) -> list[tuple[Path, str]]:
    out = []
    for p in sorted((capture / "photos" / "room").glob("*")):
        if p.suffix.lower() in PHOTO:
            dst = workdir / "photos" / f"room_{p.stem}.jpg"
            out.append((dst if dst.exists() else _normalize(p, dst), "room"))
    return out


def item_media(capture: Path, workdir: Path, entries: list[dict]) -> tuple[dict[str, list[Path]], list[tuple[dict, Path]]]:
    closeups, notes = {}, []
    for e in entries:
        d = capture / "items" / e["id"]
        if not d.is_dir():
            continue
        shots = [p for p in sorted(d.glob("*")) if p.suffix.lower() in PHOTO]
        closeups[e["id"]] = [_normalize(p, workdir / "photos" / f"item_{e['id']}_{p.stem}.jpg") for p in shots]
        note = next((p for p in sorted(d.glob("voice.*")) if p.suffix.lower() in AUDIO), None)
        if note:
            notes.append((e, note))
    return closeups, notes


def _first(capture: Path, stem: str, suffixes) -> Path | None:
    return next((p for p in sorted(capture.glob(f"{stem}.*")) if p.suffix.lower() in suffixes), None)


def detect(capture: Path) -> dict:
    workdir = capture / "out"
    workdir.mkdir(exist_ok=True)
    session.update(capture, lambda d: d.update(stage="detecting"))
    _status(workdir, "detect", "running")
    photos = room_photos(capture, workdir)
    if not photos:
        raise ValueError("no room photos in the capture")
    items, log = local.detect(photos, progress=lambda **kw: _status(workdir, "detect", "running", **kw))
    (workdir / "detect_log.json").write_text(json.dumps(log, indent=1, default=str))
    entries = session.from_detection(items, workdir / "photos", workdir / "thumbs")
    data = session.update(capture, lambda d: d.update(stage="review", items=entries, photos=[p.name for p, _ in photos]))
    _status(workdir, "detect", "done", items=len(entries))
    return data


def value(capture: Path, backend: str = "opus") -> dict:
    workdir = capture / "out"
    meta = json.loads((capture / "meta.json").read_text()) if (capture / "meta.json").exists() else {}
    room, city = meta.get("room") or "room", meta.get("city") or "India"
    t0 = time.time()
    session.update(capture, lambda d: d.update(stage="valuing"))
    entries = session.active(session.load(capture))
    photos = room_photos(capture, workdir)
    closeups, notes = item_media(capture, workdir, entries)
    names = {e["id"]: e["name"] for e in entries}
    all_photos = photos + [(p, f"close-up of the {names[eid]}") for eid, ps in closeups.items() for p in ps]
    by_name = {p.name: p for p, _ in photos}

    results: dict[str, SourceResult] = {}
    errors: dict[str, str] = {}

    def guarded(name, fn, *args, **kw):
        _status(workdir, name, "running")
        try:
            results[name] = fn(*args, **kw)
            (workdir / f"{name}.json").write_text(results[name].model_dump_json(indent=1))
            _status(workdir, name, "done", items=len(results[name].items), seconds=results[name].seconds)
        except Exception as e:  # one broken source must not sink the other two
            errors[name] = f"{type(e).__name__}: {e}"
            (workdir / f"{name}_error.txt").write_text(traceback.format_exc())
            _status(workdir, name, "failed", error=errors[name])

    with ThreadPoolExecutor(1) as pool:  # the frontier model is remote, it runs beside the GPU work
        remote = pool.submit(guarded, "frontier", frontier.run, backend, all_photos, city, workdir) if backend != "none" else None
        guarded("local", local.value, entries, closeups, by_name, workdir,
                progress=lambda **kw: _status(workdir, "local", "running", **kw))
        room_note = _first(capture, "voice", AUDIO)
        if notes or room_note:
            guarded("voice", voice.run_items, notes, room_note, workdir,
                    progress=lambda **kw: _status(workdir, "voice", "running", **kw))
        if remote:
            remote.result()

    _status(workdir, "area", "running")
    tape = area.from_tape(meta["length_cm"], meta["width_cm"]) if meta.get("length_cm") and meta.get("width_cm") else None
    fp = None
    if not tape and meta.get("run_floorplan", True):
        fp = area.from_floorplan(room, [p for p, _ in photos], _first(capture, "video", VIDEO), workdir)
    fr = results.get("frontier")
    area_info = area.pick(tape, fp, fr.room_area_m2 if fr else None)
    _status(workdir, "area", "done", source=area_info.get("source"))

    _status(workdir, "jev", "running")
    sources = [results[k].items for k in ("local", "frontier", "voice") if k in results]
    groups, pairs, skipped = jev.align(sources)
    answers = jev.rank_groups(groups)
    lines = valuation.line_items(groups, answers)
    _status(workdir, "jev", "done", groups=len(groups), pairs=len(pairs), pairs_skipped=skipped)

    everything = session.load(capture)["items"]
    shelves = {k: results[k].shelves for k in ("local", "frontier") if k in results and results[k].shelves is not None}
    report = {
        "room": room, "city": city, "backend": BACKEND_NAMES[backend],
        "area": area_info, "shelves": shelves, "totals": valuation.totals(lines),
        "leaderboard": valuation.leaderboard(lines), "items": lines,
        "sources": {k: {"items": len(v.items), "seconds": v.seconds, "notes": v.notes} for k, v in results.items()},
        "review": {"kept": len(entries), "removed": sum(1 for e in everything if e["state"] == "removed"),
                   "added": sum(1 for e in entries if e["state"] == "added"),
                   "closeups": sum(len(v) for v in closeups.values()), "voice_notes": len(notes)},
        "errors": errors, "jev_pairs_scored": len(pairs), "jev_pairs_skipped": skipped,
        "seconds": round(time.time() - t0, 1),
    }
    (workdir / "report.json").write_text(json.dumps(report, indent=1, default=str))
    (workdir / "jev_pairs.json").write_text(json.dumps(pairs, indent=1))
    session.update(capture, lambda d: d.update(stage="done"))
    _status(workdir, "report", "done", seconds=report["seconds"])
    return report


def run(capture: Path, backend: str = "opus") -> dict:
    """Command line: detect, keep every detected item as is, then value."""
    if session.load(capture).get("stage") in (None, "new", "detecting"):
        detect(capture)
    return value(capture, backend)
