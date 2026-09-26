"""Floor area and layout. Priority: tape dimensions typed on the capture page, then the
floor plan take-home pipeline run on the room photos (photo tier: VGGT plus MoGe-2 scale),
then the frontier model's estimate. Every answer says where it came from."""

import json
import shutil
import subprocess
from pathlib import Path

FLOORPLAN_REPO = Path(__file__).resolve().parents[3] / "floorplan-takehome"
SQFT_PER_M2 = 10.7639


def from_tape(length_cm: float, width_cm: float, source: str = "tape measurement", ceiling_cm: float | None = None) -> dict:
    m2 = length_cm * width_cm / 1e4
    out = {"area_m2": round(m2, 2), "area_sqft": round(m2 * SQFT_PER_M2), "source": source,
           "dimensions_cm": [length_cm, width_cm]}
    if ceiling_cm:
        out["ceiling_cm"] = ceiling_cm
    return out


def from_plan_file(plan_json: Path) -> dict | None:
    """A plan the floor plan take-home already made of this room (e.g. its ARCore depth tier)."""
    if not plan_json.exists():
        return None
    p = json.loads(plan_json.read_text())
    rooms = p.get("rooms") or []
    if not rooms or not rooms[0].get("area_m2"):
        return None
    r = rooms[0]
    png = plan_json.with_suffix(".png")
    return {"area_m2": round(r["area_m2"], 2), "area_sqft": round(r["area_m2"] * SQFT_PER_M2),
            "interval_m2": r.get("area_interval_m2"), "wall_lengths_cm": r.get("wall_lengths_cm"),
            "source": f"floor plan pipeline, {r.get('source_tier', 'existing')} tier ({plan_json.parent.name})",
            "plan_png": str(png) if png.exists() else None}


def from_floorplan(room: str, photos: list[Path], video: Path | None, workdir: Path, timeout_s: int = 1500) -> dict | None:
    """Hand the photos to the floor plan pipeline as a files-only capture."""
    if not (FLOORPLAN_REPO / "scripts" / "floorplan.py").exists():
        return None
    cap = workdir / "floorplan"
    (cap / "photos" / room).mkdir(parents=True, exist_ok=True)
    for p in photos:
        shutil.copy(p, cap / "photos" / room / p.name)
    if video:
        shutil.copy(video, cap / f"video{video.suffix}")
    (cap / "capture.json").write_text(json.dumps({"captures": [], "upload": {"kind": "files", "room": room}}))
    # a replay: the floor plan was already computed from these photos
    if not any((cap / n).exists() for n in ("plan_photos.json", "plan_video.json")):
        try:
            subprocess.run(["uv", "run", "--project", str(FLOORPLAN_REPO), "python", "scripts/floorplan.py", str(cap)],
                           cwd=FLOORPLAN_REPO, capture_output=True, text=True, timeout=timeout_s, check=True)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            (workdir / "floorplan_error.txt").write_text(str(getattr(e, "stderr", e))[-4000:])
            return None
    for name, tier in (("plan_video.json", "video"), ("plan_photos.json", "photos")):
        f = cap / name
        if not f.exists():
            continue
        rooms = json.loads(f.read_text()).get("rooms") or []
        if rooms and rooms[0].get("area_m2"):
            r = rooms[0]
            png = cap / name.replace(".json", ".png")
            return {"area_m2": round(r["area_m2"], 2), "area_sqft": round(r["area_m2"] * SQFT_PER_M2),
                    "interval_m2": r.get("area_interval_m2"), "wall_lengths_cm": r.get("wall_lengths_cm"),
                    "source": f"floor plan pipeline, {tier} tier", "plan_png": str(png) if png.exists() else None}
    return None


def pick(tape: dict | None, floorplan: dict | None, frontier_m2: float | None, *more: dict | None) -> dict:
    candidates = [c for c in (tape, *more, floorplan) if c]
    if frontier_m2:
        candidates.append({"area_m2": round(frontier_m2, 2), "area_sqft": round(frontier_m2 * SQFT_PER_M2),
                           "source": "frontier model estimate from photos"})
    if not candidates:
        return {"area_m2": None, "source": "none", "candidates": []}
    best = dict(candidates[0])
    if not best.get("plan_png"):  # the tape gives the number, a measured plan still gives the picture
        best["plan_png"] = next((c["plan_png"] for c in candidates if c.get("plan_png")), None)
    return {**best, "candidates": candidates}
