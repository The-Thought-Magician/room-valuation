"""Room contents valuation for insurance: local models, a frontier model and the owner's voice,
combined by Jev."""

import os
from pathlib import Path


def _load_env():
    """Read KEY=value lines from the repo's .env (git-ignored) without overriding the shell."""
    env = Path(__file__).resolve().parents[2] / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            key, sep, value = line.strip().partition("=")
            if sep and key and not key.startswith("#"):
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env()
# No Python headers on this machine, so Triton cannot build its JIT kernels: keep torch on
# its eager paths. Must be set before torch is imported anywhere.
os.environ.setdefault("TORCH_COMPILE_DISABLE", "1")
os.environ.setdefault("TORCH_DISABLE_NATIVE_JIT", "1")
# Weights are fetched once by scripts/fetch_weights.sh. After that the Hub is never asked:
# a stalled update check on a dead connection hung a whole valuation (2026-09-26).
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")


def main() -> None:
    import argparse
    import json

    ap = argparse.ArgumentParser(prog="room-valuation")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="value one capture folder")
    r.add_argument("capture")
    r.add_argument("--backend", choices=["opus", "astra", "none"], default="opus")
    v = sub.add_parser("revalue", help="re-run the valuation of a reviewed capture, reusing saved sources")
    v.add_argument("capture")
    v.add_argument("--reuse", default="frontier,local,voice", help="comma list: frontier, local, voice load out/<source>.json; "
                                                                "refine keeps the local close-up reading and re-prices")
    v.add_argument("--backend", choices=["opus", "astra", "none"], default="opus")
    sc = sub.add_parser("score", help="score a report against a ground truth file")
    sc.add_argument("capture")
    sc.add_argument("--truth", default="data/ground_truth/bedroom.json")
    s = sub.add_parser("serve", help="start the capture backend")
    s.add_argument("--port", type=int, default=8100)
    args = ap.parse_args()
    if args.cmd == "revalue":
        from room_valuation.run import value
        from room_valuation.score import score

        rep = value(Path(args.capture), args.backend, tuple(s for s in args.reuse.split(",") if s))
        print(json.dumps({"totals": {k: rep["totals"][k] for k in ("rcv_inr", "acv_inr", "items", "needs_review",
                                                                        "possible_double_count_inr")}}, indent=1))
        if Path("data/ground_truth/bedroom.json").exists():
            print(score(rep, json.loads(Path("data/ground_truth/bedroom.json").read_text()))["summary"])
        return
    if args.cmd == "score":
        from room_valuation.score import score

        rep = json.loads((Path(args.capture) / "out" / "report.json").read_text())
        out = score(rep, json.loads(Path(args.truth).read_text()))
        print(json.dumps(out, indent=1, default=str))
        return
    if args.cmd == "run":
        from room_valuation.run import run

        rep = run(Path(args.capture), args.backend)
        print(json.dumps({"totals": rep["totals"], "area": rep["area"], "errors": rep["errors"]}, indent=1, default=str))
    else:
        import uvicorn

        uvicorn.run("room_valuation.server:app", host="127.0.0.1", port=args.port)
