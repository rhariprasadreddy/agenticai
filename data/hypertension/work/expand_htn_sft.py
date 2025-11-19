#!/usr/bin/env python3
import json
import random
from pathlib import Path
from copy import deepcopy

# This file lives at: data/hypertension/work/expand_htn_sft.py
# Repo root          = /home/agenticai/agenticai -> parents[3]
ROOT = Path(__file__).resolve().parents[3]

IN_PATH = ROOT / "data/hypertension/curated/train_htn_seed.jsonl"
OUT_PATH = ROOT / "data/hypertension/curated/train_htn_expanded.jsonl"
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

USER_VARIANTS = [
    "Please customize based on hypertension and salt restriction.",
    "Keep in mind DASH principles and low sodium.",
    "Avoid high-salt foods; suggest potassium-rich options.",
    "Plan should support better blood pressure control.",
    "Include justification with sodium and fat considerations.",
]


def perturb_user(msg: str) -> str:
    """Add small variation to user request."""
    variant = random.choice(USER_VARIANTS)
    return msg + "\n" + variant


def perturb_assistant(msg: str) -> str:
    """Add small permissible variations."""
    repl = [
        ("Why:", "Reason:"),
        ("sodium", "salt intake"),
        ("blood pressure", "BP control"),
        ("fiber", "dietary fiber"),
    ]
    out = msg
    # choose up to 2 replacements randomly (if fewer exist, that's OK)
    k = min(2, len(repl))
    for a, b in random.sample(repl, k=k):
        out = out.replace(a, b)
    return out


def expand_record(rec: dict) -> dict:
    msgs = deepcopy(rec["messages"])
    for m in msgs:
        if m.get("role") == "user":
            m["content"] = perturb_user(m.get("content", ""))
        elif m.get("role") == "assistant":
            m["content"] = perturb_assistant(m.get("content", ""))
    return {"messages": msgs}


def main():
    if not IN_PATH.exists():
        print(f"❌ Seed HTN file not found: {IN_PATH}")
        return

    seeds = []
    with IN_PATH.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            seeds.append(json.loads(line))

    if not seeds:
        print(f"❌ No seed records loaded from {IN_PATH}")
        return

    N = 2000  # final target
    out = []

    for _ in range(N):
        rec = random.choice(seeds)
        out.append(expand_record(rec))

    with OUT_PATH.open("w") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"Created {len(out)} expanded HTN samples → {OUT_PATH}")


if __name__ == "__main__":
    main()

