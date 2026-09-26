"""FastAPI backend: the phone uploads a capture, one worker thread runs it (one GPU), the
results page polls status and renders the report."""

import json
import queue
import re
import secrets
import threading
import time
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse

from room_valuation import run as runner

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "captures"
WEB = ROOT / "web"
ID_RE = re.compile(r"^[0-9]{8}-[0-9]{6}-[0-9a-f]{6}$")
PHOTO_EXT = {".jpg", ".jpeg", ".png", ".webp"}
MEDIA_EXT = set(runner.AUDIO) | set(runner.VIDEO)
MAX_BYTES = 300 * 1024 * 1024

app = FastAPI(title="room-valuation")
jobs: queue.Queue = queue.Queue()


def _worker():
    while True:
        cap, backend = jobs.get()
        try:
            runner.run(cap, backend)
        except Exception as e:
            (cap / "out").mkdir(exist_ok=True)
            (cap / "out" / "failed.txt").write_text(f"{type(e).__name__}: {e}")
        jobs.task_done()


threading.Thread(target=_worker, daemon=True).start()


def _capture_dir(cid: str) -> Path:
    if not ID_RE.match(cid):
        raise HTTPException(404)
    d = DATA / cid
    if not d.is_dir():
        raise HTTPException(404)
    return d


async def _save(upload: UploadFile, dst: Path, allowed: set[str]) -> None:
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix not in allowed:
        raise HTTPException(400, f"file type {suffix or '?'} not accepted")
    size = 0
    dst = dst.with_suffix(suffix)
    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("wb") as f:
        while chunk := await upload.read(1 << 20):
            size += len(chunk)
            if size > MAX_BYTES:
                raise HTTPException(413, "file too large")
            f.write(chunk)


@app.get("/", response_class=HTMLResponse)
def index():
    return (WEB / "index.html").read_text()


@app.get("/r/{cid}", response_class=HTMLResponse)
def results_page(cid: str):
    _capture_dir(cid)
    return (WEB / "results.html").read_text()


@app.get("/health")
def health():
    return {"ok": True, "queued": jobs.qsize()}


@app.post("/api/captures")
async def create(room: str = Form("bedroom"), city: str = Form("Rourkela"), length_cm: float | None = Form(None),
                 width_cm: float | None = Form(None), backend: str = Form("opus"),
                 room_photos: list[UploadFile] = File(default=[]), book_photos: list[UploadFile] = File(default=[]),
                 voice: UploadFile | None = File(None), video: UploadFile | None = File(None)):
    if backend not in ("opus", "astra", "none"):
        raise HTTPException(400, "backend must be opus, astra or none")
    if not room_photos and not book_photos:
        raise HTTPException(400, "at least one photo is needed")
    cid = time.strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(3)
    cap = DATA / cid
    for i, f in enumerate(room_photos):
        await _save(f, cap / "photos" / "room" / f"{i:03d}", PHOTO_EXT)
    for i, f in enumerate(book_photos):
        await _save(f, cap / "photos" / "books" / f"{i:03d}", PHOTO_EXT)
    if voice and voice.filename:
        await _save(voice, cap / "voice", MEDIA_EXT)
    if video and video.filename:
        await _save(video, cap / "video", MEDIA_EXT)
    meta = {"room": re.sub(r"[^\w -]", "", room)[:40] or "room", "city": re.sub(r"[^\w -]", "", city)[:40],
            "length_cm": length_cm, "width_cm": width_cm}
    (cap / "meta.json").write_text(json.dumps(meta))
    jobs.put((cap, backend))
    return {"id": cid, "results": f"/r/{cid}"}


@app.get("/api/captures/{cid}/status")
def status(cid: str):
    d = _capture_dir(cid) / "out"
    if (d / "failed.txt").exists():
        return {"failed": (d / "failed.txt").read_text()}
    if (d / "status.json").exists():
        return json.loads((d / "status.json").read_text())
    return {"queued": True}


@app.get("/api/captures/{cid}/report")
def report(cid: str):
    f = _capture_dir(cid) / "out" / "report.json"
    if not f.exists():
        raise HTTPException(404, "not ready")
    return json.loads(f.read_text())


@app.get("/api/captures/{cid}/photo/{name}")
def photo(cid: str, name: str):
    if not re.match(r"^[\w.-]+\.jpg$", name):
        raise HTTPException(404)
    f = _capture_dir(cid) / "out" / "photos" / name
    if not f.exists():
        raise HTTPException(404)
    return FileResponse(f)


@app.get("/api/captures/{cid}/plan.png")
def plan_png(cid: str):
    rep = report(cid)
    png = (rep.get("area") or {}).get("plan_png")
    if not png or not Path(png).exists():
        raise HTTPException(404)
    return FileResponse(png)
