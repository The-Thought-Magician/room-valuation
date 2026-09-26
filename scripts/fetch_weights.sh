#!/usr/bin/env bash
# Download every model once (the app runs with HF_HUB_OFFLINE=1 afterwards).
set -euo pipefail
cd "$(dirname "$0")/.."
export HF_HUB_OFFLINE=0 HF_HUB_DISABLE_XET=1
for m in google/owlv2-base-patch16-ensemble Qwen/Qwen3-VL-2B-Instruct openai/whisper-large-v3-turbo; do
  uv run hf download "$m" >/dev/null && echo "ok $m"
done
