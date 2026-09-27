"""3D for the room photos, run inside the floor plan take-home's environment (it has VGGT and
MoGe-2). Called by room_valuation.geometry, not by hand:

    uv run --project ~/dev/cozmo/floorplan-takehome python scripts/geometry_worker.py <out.npz> <image> [<image> ...]

- VGGT-1B gives every pixel a 3D point and every image a camera, in one world frame.
- Any number of images: they go through VGGT in chunks of CHUNK that share OVERLAP images. Each
  chunk is aligned to the first by a similarity transform (Umeyama) fitted on the pixels of the
  shared images, so a long video works on the 8 GB card.
- MoGe-2 monocular metric depth gives the metric scale (the take-home's moge_scale).
- The camera up axes give a rotation that makes world y point up.
Writes points (float16), confidence, per-image world-to-camera rotation and camera centre, the
metric scale and the level rotation.
"""

import importlib.util
import os
import sys
from pathlib import Path

import numpy as np

# geometry.py by its path: this runs in the take-home's environment, where room_valuation is not installed
_GEOMETRY_PY = Path(__file__).resolve().parents[1] / "src" / "room_valuation" / "geometry.py"
_spec = importlib.util.spec_from_file_location("geometry", _GEOMETRY_PY)
_geometry = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_geometry)
umeyama = _geometry.umeyama

CHUNK = int(os.environ.get("GEOMETRY_CHUNK", 24))  # 24 images peaked at 5.2 GB on the RTX 5050
OVERLAP = 6


def chunks(n: int) -> list[list[int]]:
    if n <= CHUNK:
        return [list(range(n))]
    out, start = [], 0
    while start < n - OVERLAP:
        out.append(list(range(start, min(n, start + CHUNK))))
        start += CHUNK - OVERLAP
    return out


def main():
    from floorplan_takehome.multiview import level_by_camera_up, moge_scale, release_vggt, run_vggt

    out_path, paths = Path(sys.argv[1]), sys.argv[2:]
    n = len(paths)
    points = conf = None
    rot_wc = np.zeros((n, 3, 3), np.float32)
    centre = np.zeros((n, 3), np.float32)
    fits = []
    for c, idx in enumerate(chunks(n)):
        res = run_vggt([paths[i] for i in idx])
        pts, cf, ext = res["points"], res["conf"], res["extrinsic"]
        if points is None:
            points = np.zeros((n, *pts.shape[1:]), np.float32)
            conf = np.zeros((n, *cf.shape[1:]), np.float32)
        r, t = ext[:, :, :3], ext[:, :, 3]
        cen = -np.einsum("sji,sj->si", r, t)  # camera centre = -R^T t
        s, rot, tr = 1.0, np.eye(3), np.zeros(3)
        if c > 0:  # align this chunk to the world of the chunks before it, on the shared images
            shared = [k for k, i in enumerate(idx) if i < idx[0] + OVERLAP]
            src, dst = [], []
            for k in shared:
                i = idx[k]
                good = (cf[k] >= np.percentile(cf[k], 50)) & (conf[i] >= np.percentile(conf[i], 50))
                src.append(pts[k][good])
                dst.append(points[i][good])
            src, dst = np.concatenate(src), np.concatenate(dst)
            pick = np.random.default_rng(0).choice(len(src), min(len(src), 40000), replace=False)
            s, rot, tr = umeyama(src[pick].astype(np.float64), dst[pick].astype(np.float64))
            resid = np.median(np.linalg.norm((s * src[pick] @ rot.T + tr) - dst[pick], axis=1))
            fits.append({"chunk": c, "scale": round(s, 4), "median_residual": round(float(resid), 4)})
        for k, i in enumerate(idx):
            if c > 0 and i < idx[0] + OVERLAP:
                continue  # the earlier chunk already placed this image
            points[i] = s * pts[k] @ rot.T + tr
            conf[i] = cf[k]
            rot_wc[i] = r[k] @ rot.T
            centre[i] = s * rot @ cen[k] + tr
    release_vggt()
    extrinsic = np.concatenate([rot_wc, -np.einsum("sij,sj->si", rot_wc, centre)[:, :, None]], axis=2)
    scale, scale_info = moge_scale(paths, {"points": points, "conf": conf, "extrinsic": extrinsic})
    level = level_by_camera_up(extrinsic)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out_path, paths=np.array(paths), points=points.astype(np.float16), conf=conf.astype(np.float16),
                        rot_wc=rot_wc, centre=centre, scale=scale, level=level,
                        chunks=np.array(len(chunks(n))), chunk_fits=np.array([str(f) for f in fits]),
                        scale_info=np.array(str(scale_info)))
    print(f"{n} images, {len(chunks(n))} chunks, metric scale {scale:.3f}")


if __name__ == "__main__":
    main()
