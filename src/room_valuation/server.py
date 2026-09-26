"""FastAPI backend for the guided capture.

1. POST /api/captures            room details and room photos; starts detection
2. GET  /c/{id}                  detected item list: review, remove, add missing
3. GET  /c/{id}/i/{item}         one page per item: close-ups and a voice note
4. POST /api/captures/{id}/submit    starts the valuation; results at /r/{id}

One worker thread runs the jobs in order: there is one GPU."""

import json
import queue
import re
import secrets
import threading
import time
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from room_valuation import run as runner
from room_valuation import session, valuation
from room_valuation.schema import CATEGORIES

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "captures"
WEB = ROOT / "web"
ID_RE = re.compile(r"^[0-9]{8}-[0-9]{6}-[0-9a-f]{6}$")
ITEM_RE = re.compile(r"^(local|added)-[0-9]+$")
PHOTO_EXT = set(runner.PHOTO)
AUDIO_EXT = set(runner.AUDIO)
VIDEO_EXT = set(runner.VIDEO) | {".webm", ".3gp"}
MAX_BYTES = 300 * 1024 * 1024

app = FastAPI(title="room-valuation")
app.mount("/static", StaticFiles(directory=WEB / "static"), name="static")
jobs: queue.Queue = queue.Queue()


def _worker():
    while True:
        kind, cap, backend, reuse = jobs.get()
        try:
            runner.detect(cap) if kind == "detect" else runner.value(cap, backend, reuse)
        except Exception as e:
            (cap / "out").mkdir(exist_ok=True)
            (cap / "out" / "failed.txt").write_text(f"{kind}: {type(e).__name__}: {e}")
            session.update(cap, lambda d: d.update(stage="failed"))
        jobs.task_done()


threading.Thread(target=_worker, daemon=True).start()


def _capture_dir(cid: str) -> Path:
    if not ID_RE.match(cid):
        raise HTTPException(404)
    d = DATA / cid
    if not d.is_dir():
        raise HTTPException(404)
    return d


async def _save(upload: UploadFile, dst: Path, allowed: set[str]) -> Path:
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
    return dst


def _page(name: str) -> str:
    return (WEB / name).read_text()


@app.get("/", response_class=HTMLResponse)
def index():
    return _page("index.html")


@app.get("/record", response_class=HTMLResponse)
def record_page():
    return _page("record.html")


@app.get("/c/{cid}", response_class=HTMLResponse)
def items_page(cid: str):
    _capture_dir(cid)
    return _page("items.html")


@app.get("/c/{cid}/i/{iid}", response_class=HTMLResponse)
def item_page(cid: str, iid: str):
    _capture_dir(cid)
    if not ITEM_RE.match(iid):
        raise HTTPException(404)
    return _page("item.html")


@app.get("/r/{cid}", response_class=HTMLResponse)
def results_page(cid: str):
    _capture_dir(cid)
    return _page("results.html")


@app.get("/health")
def health():
    return {"ok": True, "queued": jobs.qsize()}


@app.post("/api/captures")
async def create(room: str = Form("bedroom"), city: str = Form(""), length_cm: float | None = Form(None),
                 width_cm: float | None = Form(None), room_photos: list[UploadFile] = File(default=[]),
                 voice: UploadFile | None = File(None), video: UploadFile | None = File(None)):
    if not room_photos and not (video and video.filename):
        raise HTTPException(400, "record a room video or take at least one room photo")
    cid = time.strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(3)
    cap = DATA / cid
    for i, f in enumerate(room_photos):
        await _save(f, cap / "photos" / "room" / f"{i:03d}", PHOTO_EXT)
    if voice and voice.filename:
        await _save(voice, cap / "voice", AUDIO_EXT)
    if video and video.filename:
        await _save(video, cap / "video", VIDEO_EXT)
    meta = {"room": re.sub(r"[^\w -]", "", room)[:40] or "room", "city": re.sub(r"[^\w -]", "", city)[:40],
            "length_cm": length_cm, "width_cm": width_cm}
    (cap / "meta.json").write_text(json.dumps(meta))
    session.save(cap, {"stage": "queued", "items": [], "meta": meta})
    jobs.put(("detect", cap, None, ()))
    return {"id": cid, "next": f"/c/{cid}"}


@app.get("/api/captures/{cid}/session")
def get_session(cid: str):
    cap = _capture_dir(cid)
    data = session.load(cap)
    status = cap / "out" / "status.json"
    data["status"] = json.loads(status.read_text()) if status.exists() else None
    failed = cap / "out" / "failed.txt"
    data["failed"] = failed.read_text() if failed.exists() else None
    for e in data["items"]:
        d = cap / "items" / e["id"]
        e["closeup_count"] = len([p for p in d.glob("*") if p.suffix.lower() in PHOTO_EXT]) if d.is_dir() else 0
        e["voice_count"] = len([p for p in d.glob("voice*") if p.suffix.lower() in AUDIO_EXT]) if d.is_dir() else 0
        e["has_voice"] = e["voice_count"] > 0
    data["categories"] = CATEGORIES
    return data


@app.post("/api/captures/{cid}/detect")
def retry_detect(cid: str):
    """Run detection again on what was already uploaded (after a failure, or with new settings)."""
    cap = _capture_dir(cid)
    if session.load(cap).get("stage") in ("queued", "detecting", "queued_value", "valuing"):
        raise HTTPException(409, "a job for this capture is already running")
    for f in ("status.json", "failed.txt"):
        (cap / "out" / f).unlink(missing_ok=True)
    session.update(cap, lambda d: d.update(stage="queued"))
    jobs.put(("detect", cap, None, ()))
    return {"ok": True}


@app.post("/api/captures/{cid}/items/{iid}")
async def save_item(cid: str, iid: str, quantity: int | None = Form(None), name: str | None = Form(None),
                    state: str | None = Form(None), note: str | None = Form(None),
                    closeups: list[UploadFile] = File(default=[]),
                    voice: UploadFile | None = File(None)):
    cap = _capture_dir(cid)
    if not ITEM_RE.match(iid):
        raise HTTPException(404)
    data = session.load(cap)
    if not any(e["id"] == iid for e in data["items"]):
        raise HTTPException(404)
    d = cap / "items" / iid
    start = len(list(d.glob("*"))) if d.is_dir() else 0
    for i, f in enumerate(closeups):
        await _save(f, d / f"closeup_{start + i:03d}", PHOTO_EXT)
    if voice and voice.filename:  # every recording is kept; all of an item's notes are read together
        await _save(voice, d / f"voice_{len(list(d.glob('voice*'))):02d}", AUDIO_EXT)

    def edit(s):
        for e in s["items"]:
            if e["id"] == iid:
                if quantity is not None:
                    e["quantity"] = max(1, min(999, quantity))
                if name:
                    e["name"] = re.sub(r"[^\w .,'()/-]", "", name)[:80] or e["name"]
                if note is not None:
                    e["note"] = note.strip()[:500]
                if state == "removed":
                    e["state"] = "removed"
                elif state == "restore" and e["state"] == "removed":
                    e["state"] = "added" if iid.startswith("added-") else "detected"

    session.update(cap, edit)
    return {"ok": True}


@app.post("/api/captures/{cid}/items")
async def add_item(cid: str, name: str = Form(...), category: str = Form("other"), quantity: int = Form(1)):
    cap = _capture_dir(cid)
    if category not in CATEGORIES:
        raise HTTPException(400, "unknown category")
    new = {}

    def add(s):
        n = 1 + sum(1 for e in s["items"] if e["id"].startswith("added-"))
        new.update({"id": f"added-{n}", "state": "added", "category": category,
                    "name": re.sub(r"[^\w .,'()/-]", "", name)[:80] or category, "brand": None, "model": None,
                    "quantity": max(1, min(999, quantity)), "thumb": None, "closeups": [], "voice": None, "note": ""})
        s["items"].append(dict(new))

    session.update(cap, add)
    return {"id": new["id"], "next": f"/c/{cid}/i/{new['id']}"}


@app.post("/api/captures/{cid}/submit")
def submit(cid: str, backend: str = Form("opus"), reuse: str = Form("")):
    cap = _capture_dir(cid)
    if backend not in runner.BACKEND_NAMES:
        raise HTTPException(400, "backend must be opus, astra or none")
    if session.load(cap).get("stage") not in ("review", "failed", "done"):
        raise HTTPException(409, "detection is not finished")
    for f in ("status.json", "failed.txt", "report.json"):
        (cap / "out" / f).unlink(missing_ok=True)
    session.update(cap, lambda d: d.update(stage="queued_value"))
    jobs.put(("value", cap, backend, tuple(s for s in reuse.split(",") if s in runner.REPLAYABLE + ("refine", "transcripts"))))
    return {"results": f"/r/{cid}"}


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
    cap = _capture_dir(cid)
    f = cap / "out" / "report.json"
    if not f.exists():
        raise HTTPException(404, "not ready")
    return valuation.reviewed_report(json.loads(f.read_text()), session.load(cap).get("line_review") or {})


@app.post("/api/captures/{cid}/review")
def review_line(cid: str, key: str = Form(...), action: str = Form(...), of: str | None = Form(None)):
    """The owner's final review on the results page: remove a line, mark it a duplicate of
    another, or undo. Totals recompute on the next read; no re-run needed."""
    cap = _capture_dir(cid)
    if action not in ("remove", "duplicate", "keep"):
        raise HTTPException(400, "action must be remove, duplicate or keep")
    rep = json.loads((cap / "out" / "report.json").read_text())
    keys = {ln["key"] for ln in rep["items"] if "key" in ln}
    if key not in keys or (action == "duplicate" and of not in keys):
        raise HTTPException(404, "unknown line")

    def edit(s):
        r = s.setdefault("line_review", {})
        if action == "keep":
            r.pop(key, None)
        else:
            r[key] = {"action": action, "of": of if action == "duplicate" else None, "t": round(time.time())}

    session.update(cap, edit)
    return {"ok": True}


def _file(cid: str, sub: str, name: str) -> FileResponse:
    if not re.match(r"^[\w.-]+\.jpg$", name):
        raise HTTPException(404)
    f = _capture_dir(cid) / "out" / sub / name
    if not f.exists():
        raise HTTPException(404)
    return FileResponse(f)


@app.get("/api/captures/{cid}/photo/{name}")
def photo(cid: str, name: str):
    return _file(cid, "photos", name)


@app.get("/api/captures/{cid}/thumb/{name}")
def thumb(cid: str, name: str):
    return _file(cid, "thumbs", name)


@app.get("/api/captures/{cid}/plan.png")
def plan_png(cid: str):
    rep = report(cid)
    png = (rep.get("area") or {}).get("plan_png")
    if not png or not Path(png).exists():
        raise HTTPException(404)
    return FileResponse(png)
