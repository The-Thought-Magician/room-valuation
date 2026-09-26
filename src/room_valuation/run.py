"""One capture in, one valuation out.

Capture folder layout (what the capture page uploads):
    meta.json            {"room": "bedroom", "city": "Rourkela", "length_cm": null, "width_cm": null}
    photos/room/*.jpg    wide shots of the room and its contents
    photos/books/*.jpg   close-ups of book spines and of labels on valuable things
    voice.*              the owner's narration (webm, m4a, mp3, wav)
    video.*              optional walkthrough, used only for floor area
"""

import json
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageOps

from room_valuation import area, frontier, jev, local, valuation, voice
from room_valuation.schema import SourceResult

BACKEND_NAMES = {"opus": "claude-opus-5-5", "astra": "gpt-6-astra", "none": "skipped (test run)"}
AUDIO = (".webm", ".m4a", ".mp3", ".wav", ".ogg", ".aac")
VIDEO = (".mp4", ".mov", ".mkv")


def _status(workdir: Path, stage: str, state: str, **extra):
    f = workdir / "status.json"
    s = json.loads(f.read_text()) if f.exists() else {"stages": {}}
    s["stages"][stage] = {"state": state, "t": round(time.time(), 1), **extra}
    s["current"] = stage
    f.write_text(json.dumps(s, indent=1))


def _prepare(capture: Path, workdir: Path) -> list[tuple[Path, str]]:
    """EXIF-upright, at most 2048 px on the long side, JPEG. Phones store rotation in EXIF."""
    out = []
    for tag in ("room", "books"):
        for p in sorted((capture / "photos" / tag).glob("*")):
            if p.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
                continue
            im = ImageOps.exif_transpose(Image.open(p)).convert("RGB")
            im.thumbnail((2048, 2048))
            dst = workdir / "photos" / f"{tag}_{p.stem}.jpg"
            dst.parent.mkdir(parents=True, exist_ok=True)
            im.save(dst, quality=90)
            out.append((dst, tag))
    return out


def _first(capture: Path, suffixes) -> Path | None:
    return next((p for p in sorted(capture.glob("*")) if p.suffix.lower() in suffixes and p.stem in ("voice", "video")), None)


def run(capture: Path, backend: str = "opus") -> dict:
    workdir = capture / "out"
    workdir.mkdir(exist_ok=True)
    meta = json.loads((capture / "meta.json").read_text()) if (capture / "meta.json").exists() else {}
    room, city = meta.get("room") or "room", meta.get("city") or "India"
    t0 = time.time()
    _status(workdir, "prepare", "running")
    photos = _prepare(capture, workdir)
    if not photos:
        raise ValueError("no photos in the capture")
    _status(workdir, "prepare", "done", photos=len(photos))

    results: dict[str, SourceResult] = {}
    errors: dict[str, str] = {}

    def guarded(name, fn, *args):
        _status(workdir, name, "running")
        try:
            results[name] = fn(*args)
            (workdir / f"{name}.json").write_text(results[name].model_dump_json(indent=1))
            _status(workdir, name, "done", items=len(results[name].items), seconds=results[name].seconds)
        except Exception as e:  # one broken source must not sink the other two
            errors[name] = f"{type(e).__name__}: {e}"
            (workdir / f"{name}_error.txt").write_text(traceback.format_exc())
            _status(workdir, name, "failed", error=errors[name])

    with ThreadPoolExecutor(1) as pool:  # the frontier model is remote, it runs beside the GPU work
        remote = pool.submit(guarded, "frontier", frontier.run, backend, photos, city, workdir) if backend != "none" else None
        guarded("local", local.run, photos, workdir)
        audio = _first(capture, AUDIO)
        if audio:
            guarded("voice", voice.run, audio, workdir)
        if remote:
            remote.result()

    _status(workdir, "area", "running")
    tape = area.from_tape(meta["length_cm"], meta["width_cm"]) if meta.get("length_cm") and meta.get("width_cm") else None
    fp = None
    if not tape and meta.get("run_floorplan", True):
        fp = area.from_floorplan(room, [p for p, tag in photos if tag == "room"], _first(capture, VIDEO), workdir)
    fr = results.get("frontier")
    area_info = area.pick(tape, fp, fr.room_area_m2 if fr else None)
    _status(workdir, "area", "done", source=area_info.get("source"))

    _status(workdir, "jev", "running")
    sources = [results[k].items for k in ("local", "frontier", "voice") if k in results]
    groups, pairs, skipped = jev.align(sources)
    answers = jev.rank_groups(groups)
    lines = valuation.line_items(groups, answers)
    _status(workdir, "jev", "done", groups=len(groups), pairs=len(pairs), pairs_skipped=skipped)

    shelves = {k: results[k].shelves for k in ("local", "frontier") if k in results and results[k].shelves is not None}
    report = {
        "room": room, "city": city, "backend": BACKEND_NAMES[backend],
        "area": area_info, "shelves": shelves, "totals": valuation.totals(lines),
        "leaderboard": valuation.leaderboard(lines), "items": lines,
        "sources": {k: {"items": len(v.items), "seconds": v.seconds, "notes": v.notes} for k, v in results.items()},
        "errors": errors, "jev_pairs_scored": len(pairs), "jev_pairs_skipped": skipped, "seconds": round(time.time() - t0, 1),
    }
    (workdir / "report.json").write_text(json.dumps(report, indent=1, default=str))
    (workdir / "jev_pairs.json").write_text(json.dumps(pairs, indent=1))
    _status(workdir, "report", "done", seconds=report["seconds"])
    return report
