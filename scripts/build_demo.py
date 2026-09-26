"""Build a self-contained demo walkthrough of one real capture: the photos, video, close-ups
and voice notes, what each pipeline read, Jev's questions and answers, and the valuation.

    uv run python scripts/build_demo.py <capture dir> <name> [--run <out/runs/<time>>]

Writes demo/<name>/ (git-ignored: it holds the owner's photos, video and voice). Open
demo/<name>/index.html directly, or http://127.0.0.1:8100/demo/<name>/ while the server runs.
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from room_valuation.schema import BUILDING  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def load(p: Path, default=None):
    return json.loads(p.read_text()) if p.exists() else default


def jpg(src: Path, dst: Path, size: int):
    im = Image.open(src)
    im.thumbnail((size, size))
    im.convert("RGB").save(dst, quality=82)


def ffmpeg(*args):
    subprocess.run(["ffmpeg", "-y", "-v", "error", *args], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("capture", type=Path)
    ap.add_argument("name")
    ap.add_argument("--run", type=Path, help="a run folder to show instead of the latest out/")
    a = ap.parse_args()
    cap, out = a.capture.resolve(), ROOT / "demo" / a.name
    run = (a.run or cap / "out").resolve()
    m = out / "media"
    shutil.rmtree(out, ignore_errors=True)
    for d in ("photos", "thumbs", "voice"):
        (m / d).mkdir(parents=True)

    photos = sorted(p.name for p in (cap / "out" / "photos").glob("*.jpg"))
    for n in photos:
        jpg(cap / "out" / "photos" / n, m / "photos" / n, 1400)
    for p in (cap / "out" / "thumbs").glob("*.jpg"):
        shutil.copy(p, m / "thumbs" / p.name)
    video = next((p for p in cap.glob("video.*")), None)
    if video:
        ffmpeg("-i", str(video), "-vf", "scale=-2:720", "-c:v", "libx264", "-crf", "28", "-preset", "veryfast",
               "-c:a", "aac", "-b:a", "64k", "-movflags", "+faststart", str(m / "video.mp4"))
    rep = load(run / "report.json")
    plan = (rep.get("area") or {}).get("plan_png")
    if plan and Path(plan).exists():
        shutil.copy(plan, m / "floor_plan.png")

    transcripts = load(cap / "out" / "transcripts.json", {})
    items = []
    for it in load(cap / "session.json")["items"]:
        d = cap / "items" / it["id"]
        voice = []
        for v in sorted(d.glob("voice_*")) if d.exists() else []:
            name = f"{it['id']}_{v.stem}.m4a"
            ffmpeg("-i", str(v), "-c:a", "aac", "-b:a", "96k", str(m / "voice" / name))
            segs = next((t for k, t in transcripts.items() if k.endswith(f"{it['id']}/{v.name}")), [])
            voice.append({"file": name, "text": " ".join(s["text"].strip() for s in segs)})
        items.append({k: it.get(k) for k in ("id", "state", "category", "name", "brand", "model", "quantity", "thumb", "note")}
                     | {"closeups": sorted(p.name for p in (cap / "out" / "photos").glob(f"item_{it['id']}_closeup_*.jpg")),
                        "voice": voice, "regions": (it.get("detected") or {}).get("regions", [])})

    jc = run / "jev_calls.jsonl"
    calls = [json.loads(ln) for ln in jc.read_text().splitlines()] if jc.exists() else []
    data = {
        "capture": cap.name,
        "meta": load(cap / "meta.json"),
        "photos": photos,
        "video": bool(video),
        "plan": (m / "floor_plan.png").exists(),
        "detections": load(cap / "out" / "detect_log.json", []),
        "items": items,
        "local_log": load(run / "local_log.json") or load(cap / "out" / "local_log.json", []),
        "local": load(run / "local.json"),
        "frontier": load(run / "frontier.json"),
        "voice": load(run / "voice.json"),
        "status": load(cap / "out" / "status.json"),
        "jev_pairs": load(run / "jev_pairs.json", []),
        "jev_calls": calls,
        "report": rep,
        "building": sorted(BUILDING),
        "score": load(run / "score.json"),
    }
    (out / "data.js").write_text("window.DEMO = " + json.dumps(data, default=str) + ";\n")
    for f in ("demo.html", "static/demo.js", "static/app.css"):
        shutil.copy(ROOT / "web" / f, out / Path(f).name.replace("demo.html", "index.html"))
    size = sum(p.stat().st_size for p in out.rglob("*") if p.is_file()) / 1e6
    print(f"{out}  ({len(photos)} photos, {sum(len(i['voice']) for i in items)} voice notes, {size:.0f} MB)")


if __name__ == "__main__":
    main()
