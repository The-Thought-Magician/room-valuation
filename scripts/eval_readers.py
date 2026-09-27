"""Score OCR and VLM choices on a capture's real photos against what they should read
(data/ground_truth/readers_<room>.json). Used to pick the models (2026-09-27).

    uv run python scripts/eval_readers.py ocr <capture> [--truth data/ground_truth/readers_bedroom.json]
    uv run python scripts/eval_readers.py vlm <capture> --model Qwen/Qwen3-VL-4B-Instruct [--int8]

OCR: the share of expected words read, per photo, for PP-OCRv6 small and medium.
VLM: category and brand on detection crops, label reading on close-ups (a wrong reading costs
half), spine titles found and titles invented.
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from room_valuation import local, models, ocr  # noqa: E402  (sets the torch flags before torch loads)
from room_valuation.schema import CATEGORIES, json_object  # noqa: E402


def words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def spine_crops(cap: Path, photos: list[str]) -> dict:
    s = json.loads((cap / "session.json").read_text())
    books = next(e for e in s["items"] if e["category"] == "book")
    boxes = {}
    for r in books["detected"]["regions"]:
        boxes.setdefault(r["photo"], []).append(r["box"])
    return {p: local._union_crop(Image.open(cap / "out" / "photos" / p).convert("RGB"), boxes[p]) for p in photos if p in boxes}


def run_ocr(cap: Path, truth: dict):
    from rapidocr import ModelType, OCRVersion, RapidOCR

    want_spines = truth["spines"]["words"].split()
    cases = [(f"spines {p}", im, want_spines, "spines") for p, im in spine_crops(cap, truth["spines"]["photos"]).items()]
    for c in truth["closeups"]:
        cases.append((c["name"], Image.open(cap / "out" / "photos" / c["photo"]).convert("RGB"), c["words"], "text"))
    for tier in (ModelType.SMALL, ModelType.MEDIUM):
        engine = RapidOCR(params={"Det.ocr_version": OCRVersion.PPOCRV6, "Det.model_type": tier,
                                  "Rec.ocr_version": OCRVersion.PPOCRV6, "Rec.model_type": tier})
        ocr._engine = lambda e=engine: e
        total, t0 = 0.0, time.time()
        for name, im, want, how in cases:
            text = " ".join(x["text"] for x in ocr.spines(im)) if how == "spines" else ocr.read_small_text(im)
            got = words(text)
            hit = [w for w in want if any(w.replace(" ", "") in g or (len(g) > 3 and g in w) for g in got)]
            total += len(hit) / len(want)
            print(f"{tier.value:6} {name:22} {len(hit)}/{len(want)}  {text[:120]}")
        print(f"{tier.value}: mean {total / len(cases):.2f}, {time.time() - t0:.0f} s\n")


def run_vlm(cap: Path, truth: dict, model_id: str, int8: bool):
    import torch

    s = json.loads((cap / "session.json").read_text())

    def crop_of(part):
        e = next(e for e in s["items"] if (e.get("detected") or {}).get("regions") and part in e["name"].lower()
                 and e["state"] != "removed")
        r = max(e["detected"]["regions"], key=lambda r: (r["box"][2] - r["box"][0]) * (r["box"][3] - r["box"][1]))
        return local._crop(Image.open(cap / "out" / "photos" / r["photo"]).convert("RGB"), r["box"])

    torch.cuda.reset_peak_memory_stats()
    vlm = models.VLM(model_id, int8)
    t0, score = time.time(), {}
    ok = 0.0
    for c in truth["crops"]:
        prompt = local.IDENTIFY.format(categories=", ".join(CATEGORIES), hint="a " + c["item"])
        ans = json_object(vlm.ask(prompt, crop_of(c["item"]), 160))
        good = ((not c.get("category") or ans.get("category") == c["category"])
                + (not c.get("brand") or c["brand"] in str(ans.get("brand") or "").lower()))
        ok += good / 2
        print(f"  crop {c['item']:16} {good}/2 {ans}")
    score["crops"] = round(ok / len(truth["crops"]), 2)
    ok = 0.0
    for c in truth["closeups"]:
        im = Image.open(cap / "out" / "photos" / c["photo"]).convert("RGB")
        prompt = local.CLOSEUP.format(name=c["name"], ocr=ocr.read_text(im) or "nothing")
        ans = json_object(vlm.ask(prompt, local._downsize(im), 200))
        blob = json.dumps(ans).lower().replace(" ", "")
        right = sum(w.replace(" ", "") in blob for w in c["words"]) / len(c["words"])
        hit = right - 0.5 * sum(w.replace(" ", "") in blob for w in c["wrong"])
        ok += hit
        print(f"  close-up {c['name']:18} {hit:.2f} {ans}")
    score["closeups"] = round(ok / len(truth["closeups"]), 2)
    titles, found, invented = truth["spines"]["titles"], set(), []
    for im in spine_crops(cap, truth["spines"]["photos"][-1:]).values():
        read = local._vlm_spine_queries(vlm.ask(local.SPINES, local._downsize(im), 400))
        norm = [re.sub(r"[^a-z0-9/ ]", "", q.lower()) for q in read]
        found = {t for t in titles if any(t in q for q in norm)}
        invented = [q for q in norm if not any(t in q for t in titles)]
    score["spines"], score["invented"] = f"{len(found)}/{len(titles)}", invented
    print(f"{model_id} int8={int8}: {score}, {time.time() - t0:.0f} s, peak {torch.cuda.max_memory_allocated() / 1e9:.1f} GB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=("ocr", "vlm"))
    ap.add_argument("capture", type=Path)
    ap.add_argument("--truth", type=Path, default=Path("data/ground_truth/readers_bedroom.json"))
    ap.add_argument("--model", default=models.VLM_ID)
    ap.add_argument("--int8", action="store_true")
    a = ap.parse_args()
    truth = json.loads(a.truth.read_text())
    run_ocr(a.capture, truth) if a.what == "ocr" else run_vlm(a.capture, truth, a.model, a.int8)


if __name__ == "__main__":
    main()
