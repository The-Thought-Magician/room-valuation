#!/usr/bin/env bash
# Start the backend on 127.0.0.1 and expose it over https with a Cloudflare quick tunnel.
# Open the printed trycloudflare.com URL on the phone (https is needed for the microphone).
set -euo pipefail
cd "$(dirname "$0")/.."
PORT="${PORT:-8100}"
uv run uvicorn room_valuation.server:app --host 127.0.0.1 --port "$PORT" &
PID=$!
trap 'kill $PID 2>/dev/null || true' EXIT
for _ in $(seq 1 40); do curl -sf "http://127.0.0.1:$PORT/health" >/dev/null && break; sleep 0.5; done
cloudflared tunnel --url "http://127.0.0.1:$PORT" --no-autoupdate
