"""Book spines with PaddleOCR's PP-OCR models, run through RapidOCR on ONNX Runtime.

PaddlePaddle itself has no Python 3.14 wheels, RapidOCR ships the same PP-OCR detection
and recognition models without the framework.

Spines on a shelf read vertically, a stack reads horizontally. The photo is read at 0, 90
and 270 degrees and the rotation with the most confident text wins. In that frame every
spine is a horizontal band, so text lines are grouped by vertical overlap: one band, one book.
"""

import functools

import numpy as np
from PIL import Image


@functools.cache
def _engine():
    """PP-OCRv6 medium, the largest tier (RapidOCR defaults to small). On the bedroom's close-ups
    and spines it read 81 percent of the known words against 72 (the Good Knight pack: 6 of 6
    against 3 of 6), about three times slower (2026-09-27, see scripts/eval_readers.py)."""
    from rapidocr import ModelType, OCRVersion, RapidOCR

    return RapidOCR(params={"Det.ocr_version": OCRVersion.PPOCRV6, "Det.model_type": ModelType.MEDIUM,
                            "Rec.ocr_version": OCRVersion.PPOCRV6, "Rec.model_type": ModelType.MEDIUM})


def _lines(image: Image.Image, min_score: float) -> list[dict]:
    res = _engine()(np.array(image))
    out = []
    for box, txt, sc in zip(res.boxes if res.boxes is not None else [], res.txts or [], res.scores or [], strict=False):
        txt = txt.strip()
        if sc < min_score or sum(c.isalnum() for c in txt) < 2:
            continue
        ys, xs = [p[1] for p in box], [p[0] for p in box]
        out.append({"text": txt, "score": float(sc), "x0": min(xs), "x1": max(xs), "y0": min(ys), "y1": max(ys),
                    "horizontal": (max(xs) - min(xs)) >= (max(ys) - min(ys))})
    return out


def _bands(lines: list[dict]) -> list[list[dict]]:
    bands: list[list[dict]] = []
    for ln in sorted(lines, key=lambda ln: (ln["y0"] + ln["y1"]) / 2):
        mid, h = (ln["y0"] + ln["y1"]) / 2, ln["y1"] - ln["y0"]
        for band in bands:
            top, bottom = min(b["y0"] for b in band), max(b["y1"] for b in band)
            if top - 0.3 * h <= mid <= bottom + 0.3 * h:
                band.append(ln)
                break
        else:
            bands.append([ln])
    return bands


def _best_rotation(image: Image.Image, min_score: float) -> tuple[int, list[dict]]:
    image = image.copy()
    image.thumbnail((1600, 1600))
    best = (0.0, 0, [])
    for rot in (0, 90, 180, 270):  # 180: a label under a laptop, photographed from the front, is upside down
        lines = _lines(image.rotate(rot, expand=True) if rot else image, min_score)
        # only text lying flat counts: in the wrong rotation the OCR still reads some vertical
        # spines, but their tall boxes all overlap and merge different books into one band
        weight = sum(ln["score"] * len(ln["text"]) for ln in lines if ln["horizontal"])
        if weight > best[0]:
            best = (weight, rot, lines)
    return best[1], best[2]


def read_text(image: Image.Image, min_score: float = 0.6) -> str:
    """All confident text on a label or sticker, row by row, joined with ' | '."""
    _, lines = _best_rotation(image, min_score)
    return " | ".join(" ".join(ln["text"] for ln in sorted(b, key=lambda ln: ln["x0"])) for b in _bands(lines))


def read_small_text(image: Image.Image, min_score: float = 0.6, grid: int = 3) -> str:
    """read_text over the whole image, then over overlapping tiles at full resolution, enlarged:
    a spec sticker on a laptop photographed from a metre away is a few dozen pixels wide, too
    small for one pass over the whole frame. New lines from the tiles are added once."""
    rot, lines = _best_rotation(image, min_score)
    seen = [" | ".join(" ".join(ln["text"] for ln in sorted(b, key=lambda ln: ln["x0"])) for b in _bands(lines))]
    if rot:  # the tiles are read upright, at the rotation that won on the whole image
        image = image.rotate(rot, expand=True)
    w, h = image.size
    if max(w, h) < 1200:
        return seen[0]
    tw, th = w // grid, h // grid
    for i in range(grid):
        for j in range(grid):
            pad_w, pad_h = tw // 4, th // 4
            box = (max(0, i * tw - pad_w), max(0, j * th - pad_h), min(w, (i + 1) * tw + pad_w), min(h, (j + 1) * th + pad_h))
            tile = image.crop(box)
            tile = tile.resize((tile.width * 2, tile.height * 2))
            text = " | ".join(" ".join(ln["text"] for ln in sorted(b, key=lambda ln: ln["x0"]))
                              for b in _bands(_lines(tile, min_score)))
            new = [s for s in text.split(" | ") if s and all(s not in t for t in seen)]
            if new:
                seen.append(" | ".join(new))
    return " | ".join(s for s in seen if s)


def spines(image: Image.Image, min_score: float = 0.6) -> list[dict]:
    """[{text, score, rotation}] one per spine band, in reading order."""
    rot, lines = _best_rotation(image, min_score)
    out = []
    for band in _bands([ln for ln in lines if ln["horizontal"]]):
        text = " ".join(ln["text"] for ln in sorted(band, key=lambda ln: ln["x0"]))
        if sum(c.isalpha() for c in text) >= 4:
            out.append({"text": text, "score": round(min(ln["score"] for ln in band), 3), "rotation": rot})
    return out
