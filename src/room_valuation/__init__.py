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


def main() -> None:
    import argparse
    import json

    ap = argparse.ArgumentParser(prog="room-valuation")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="value one capture folder")
    r.add_argument("capture")
    r.add_argument("--backend", choices=["opus", "astra"], default="opus")
    s = sub.add_parser("serve", help="start the capture backend")
    s.add_argument("--port", type=int, default=8100)
    args = ap.parse_args()
    if args.cmd == "run":
        from room_valuation.run import run

        rep = run(Path(args.capture), args.backend)
        print(json.dumps({"totals": rep["totals"], "area": rep["area"], "errors": rep["errors"]}, indent=1, default=str))
    else:
        import uvicorn

        uvicorn.run("room_valuation.server:app", host="127.0.0.1", port=args.port)
