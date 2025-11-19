#!/usr/bin/env python3
import json, random
from pathlib import Path

# Script lives at: data/hypertension/work/make_htn_splits.py
# Repo root = /home/agenticai/agenticai = parents[3]
ROOT = Path(__file__).resolve().parents[3]

IN_PATH = ROOT / "data/hypertension/curated/train_htn_expanded.jsonl"
TRAIN_PATH = ROOT / "data/hypertension/curated/train.jsonl"
VAL_PATH = ROOT / "data/hypertension/curated/val.jsonl"

random.seed(42)

samples = []
with IN_PATH.open() as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        samples.append(json.loads(line))

random.shuffle(samples)
n_total = len(samples)
n_val = max(200, int(0.1 * n_total))

val_samples = samples[:n_val]
train_samples = samples[n_val:]

TRAIN_PATH.parent.mkdir(parents=True, exist_ok=True)

with TRAIN_PATH.open("w") as f:
    for r in train_samples:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

with VAL_PATH.open("w") as f:
    for r in val_samples:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

print(f"Total: {n_total}, train: {len(train_samples)}, val: {len(val_samples)}")
print(f"Train → {TRAIN_PATH}")
print(f"Val   → {VAL_PATH}")
