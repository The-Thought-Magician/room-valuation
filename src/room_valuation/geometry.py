"""Where each detected object is in the room, and how big it is, from the room photos in 3D.

scripts/geometry_worker.py runs VGGT (a 3D point for every pixel, a camera for every photo) and
MoGe-2 (metric scale) in the floor plan take-home's environment. Here each detection box becomes
the 3D points of the object's front surface: their median is the object's position, their spread
across and up its width and height. Every view is measured on its own and the median taken, so
one bad box does not stretch the object.

Used for:
- duplicates: the same object seen in several photos sits at one place, whatever the small model
  called it each time (local._same)
- size: a listing for a much bigger or smaller product than the one measured is not this object
  (prices.size_mismatch), and a line whose measured size disagrees with the priced product is
  flagged

Sizes are estimates. On the bedroom the 15.6 inch laptop measured 37 cm wide against 36 cm, and
the 24 inch monitor 40 cm against 53 cm, so a mismatch only counts beyond a factor of 1.8.
"""

import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

FLOORPLAN_REPO = Path(__file__).resolve().parents[3] / "floorplan-takehome"
WORKER = Path(__file__).resolve().parents[2] / "scripts" / "geometry_worker.py"


class Geometry:
    def __init__(self, npz: Path, photo_dir: Path):
        z = np.load(npz, allow_pickle=True)
        self.names = [Path(p).name for p in z["paths"]]
        self.points = z["points"].astype(np.float32)
        self.conf = z["conf"].astype(np.float32)
        self.rot_wc, self.centre = z["rot_wc"], z["centre"]
        self.scale, self.level = float(z["scale"]), z["level"]
        self.chunks = int(z["chunks"])
        self.photo_dir = photo_dir
        _, self.h, self.w, _ = self.points.shape
        self._grid: dict[str, tuple] = {}

    def _image_area(self, photo: str) -> tuple[int, int, int, int, int]:
        """Index and pixel rectangle the photo fills in VGGT's padded 518 grid."""
        if photo not in self._grid:
            i = self.names.index(photo)
            pw, ph = Image.open(self.photo_dir / photo).size
            if ph >= pw:
                iw = round(pw * self.h / ph / 14) * 14
                self._grid[photo] = (i, (self.w - iw) // 2, 0, iw, self.h)
            else:
                ih = round(ph * self.w / pw / 14) * 14
                self._grid[photo] = (i, 0, (self.h - ih) // 2, self.w, ih)
        return self._grid[photo]

    def view(self, region: dict, shrink: float = 0.15) -> dict | None:
        """One sighting: position (metres, y up) and width and height (cm) of the front surface
        inside the box. The box is shrunk to stay off the background and the extent scaled back."""
        if region["photo"] not in self.names:
            return None
        i, gx, gy, gw, gh = self._image_area(region["photo"])
        x0, y0, x1, y1 = region["box"]
        bw, bh = x1 - x0, y1 - y0
        xa, xb = gx + int((x0 + shrink * bw) * gw), gx + int((x1 - shrink * bw) * gw)
        ya, yb = gy + int((y0 + shrink * bh) * gh), gy + int((y1 - shrink * bh) * gh)
        p = self.points[i, ya : yb + 1, xa : xb + 1].reshape(-1, 3)
        cf = self.conf[i, ya : yb + 1, xa : xb + 1].reshape(-1)
        p = p[cf >= np.percentile(self.conf[i], 25)]
        if len(p) < 50:
            return None
        cam = (p - self.centre[i]) @ self.rot_wc[i].T
        depth = cam[:, 2]
        near = np.abs(depth - np.percentile(depth, 35)) < 0.12 * np.median(depth)  # the object, not the wall behind
        p, cam = p[near], cam[near]
        if len(p) < 50:
            return None
        grow = self.scale * 100 / (1 - 2 * shrink)
        up = p @ self.level.T
        return {"position_m": np.median(up, 0) * self.scale,
                "width_cm": float(np.percentile(cam[:, 0], 97) - np.percentile(cam[:, 0], 3)) * grow,
                "height_cm": float(np.percentile(up[:, 1], 97) - np.percentile(up[:, 1], 3)) * grow}

    def metric_points(self, photo: str) -> tuple[np.ndarray, np.ndarray]:
        """Every pixel of one photo in metres, levelled, with its confidence."""
        i = self.names.index(photo)
        return (self.points[i].reshape(-1, 3) @ self.level.T) * self.scale, self.conf[i].reshape(-1)

    def locate(self, regions: list[dict]) -> dict | None:
        """Position and size of one object from every box it was seen in."""
        views = [v for v in (self.view(r) for r in regions) if v]
        if not views:
            return None
        pos = np.median([v["position_m"] for v in views], 0)
        spread = float(np.median([np.linalg.norm(v["position_m"] - pos) for v in views]))
        return {"position_m": [round(float(x), 2) for x in pos], "spread_m": round(spread, 2), "views": len(views),
                "width_cm": round(float(np.median([v["width_cm"] for v in views]))),
                "height_cm": round(float(np.median([v["height_cm"] for v in views])))}


def align(old: Geometry, new: Geometry, same: dict[str, str]) -> tuple[float, np.ndarray, np.ndarray] | None:
    """Similarity transform from one reconstruction's metric world to another's, fitted on the
    pixels of photos both contain (same: old name to new name, identical files)."""
    src, dst = [], []
    for o, n in same.items():
        if o in old.names and n in new.names:
            po, co = old.metric_points(o)
            pn, cn = new.metric_points(n)
            good = (co >= np.percentile(co, 50)) & (cn >= np.percentile(cn, 50))
            src.append(po[good])
            dst.append(pn[good])
    if not src:
        return None
    src, dst = np.concatenate(src), np.concatenate(dst)
    pick = np.random.default_rng(0).choice(len(src), min(len(src), 40000), replace=False)
    return umeyama(src[pick].astype(np.float64), dst[pick].astype(np.float64))


def reconstruct(photos: list[Path], workdir: Path, timeout_s: int = 3600) -> Geometry | None:
    """3D of these photos, cached in out/geometry. None when the floor plan take-home is not
    installed or the reconstruction fails; the pipeline then runs without 3D."""
    out = workdir / "geometry" / "vggt.npz"
    names = [p.name for p in photos]
    if out.exists():
        z = np.load(out, allow_pickle=True)
        if [Path(p).name for p in z["paths"]] == names:
            return Geometry(out, photos[0].parent)
    if not (FLOORPLAN_REPO / "pyproject.toml").exists() or not photos:
        return None
    log = workdir / "geometry" / "worker.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    try:
        # absolute paths: the worker runs in the take-home's folder
        proc = subprocess.run(["uv", "run", "--project", str(FLOORPLAN_REPO), "python", str(WORKER), str(out.resolve()),
                               *[str(p.resolve()) for p in photos]], cwd=FLOORPLAN_REPO, capture_output=True, text=True,
                              timeout=timeout_s)
        log.write_text(proc.stdout + proc.stderr[-6000:])
        if proc.returncode != 0 or not out.exists():
            return None
    except subprocess.TimeoutExpired:
        log.write_text("timed out")
        return None
    return Geometry(out, photos[0].parent)


def summary(geo: Geometry | None) -> dict | None:
    if geo is None:
        return None
    return {"images": len(geo.names), "chunks": geo.chunks, "metric_scale": round(geo.scale, 3),
            "method": "VGGT-1B point maps, MoGe-2 metric scale, levelled by the camera up axes"}


def umeyama(src: np.ndarray, dst: np.ndarray) -> tuple[float, np.ndarray, np.ndarray]:
    """Scale, rotation, translation with dst ~ s R src + t (least squares)."""
    mu_s, mu_d = src.mean(0), dst.mean(0)
    a, b = src - mu_s, dst - mu_d
    u, d, vt = np.linalg.svd(b.T @ a / len(src))
    sign = np.eye(3)
    if np.linalg.det(u) * np.linalg.det(vt) < 0:
        sign[2, 2] = -1
    rot = u @ sign @ vt
    scale = float(np.trace(np.diag(d) @ sign) / a.var(0).sum())
    return scale, rot, mu_d - scale * rot @ mu_s


def distance(a: dict, b: dict) -> float:
    return float(np.linalg.norm(np.array(a["position_m"]) - np.array(b["position_m"])))
