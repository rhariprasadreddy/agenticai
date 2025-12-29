#!/usr/bin/env bash
set -euo pipefail

: "${HUGGING_FACE_HUB_TOKEN:?Set HUGGING_FACE_HUB_TOKEN env (your HF token)}"

MODEL_ID="${MODEL_ID:-Qwen/Qwen2.5-1.5B-Instruct}"
TARGET_DIR="${TARGET_DIR:-/workspace/.hf/models/qwen2.5-1.5b-instruct}"

mkdir -p "$(dirname "$TARGET_DIR")"

if [ -f "$TARGET_DIR/config.json" ]; then
  echo "✅ Model already present at $TARGET_DIR"
  exit 0
fi

python - <<PY
import os
from huggingface_hub import snapshot_download
model_id = os.environ.get("MODEL_ID", "Qwen/Qwen2.5-1.5B-Instruct")
target   = os.environ.get("TARGET_DIR", "/workspace/.hf/models/qwen2.5-1.5b-instruct")
os.makedirs(target, exist_ok=True)
snapshot_download(
    repo_id=model_id,
    local_dir=target,
    local_dir_use_symlinks=False,
    token=os.environ.get("HUGGING_FACE_HUB_TOKEN"),
)
print("✅ Downloaded", model_id, "to", target)
PY

test -f "$TARGET_DIR/config.json" || { echo "❌ config.json missing under $TARGET_DIR"; exit 1; }

