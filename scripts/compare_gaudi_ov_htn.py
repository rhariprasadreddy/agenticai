#!/usr/bin/env python3
import json
from pathlib import Path

GAUDI_PATH = Path("eval/gaudi_htn_outputs.jsonl")
OV_PATH    = Path("eval/ov_htn_outputs.jsonl")

def load_jsonl(path: Path):
    out = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out

def jaccard(a, b):
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    inter = len(sa & sb)
    union = len(sa | sb) or 1
    return inter / union

def main():
    gaudi = load_jsonl(GAUDI_PATH)
    ov    = load_jsonl(OV_PATH)

    g_by_id = {r["id"]: r for r in gaudi}
    o_by_id = {r["id"]: r for r in ov}
    shared_ids = sorted(set(g_by_id) & set(o_by_id))

    print(f"🔹 Loaded {len(gaudi)} Gaudi HTN outputs and {len(ov)} Xeon OV outputs")
    print(f"🔹 Comparing {len(shared_ids)} shared prompt IDs\n")

    jaccs = []

    for pid in shared_ids:
        g = g_by_id[pid]
        o = o_by_id[pid]

        g_tokens = g["completion"].split()
        o_tokens = o["completion"].split()

        j = jaccard(g_tokens, o_tokens)
        jaccs.append(j)

        len_g = len(g_tokens)
        len_o = len(o_tokens)
        len_ratio = len_o / len_g if len_g > 0 else 0.0

        print("=" * 80)
        print(f"ID {pid}")
        print("PROMPT:", g.get("prompt", "")[:200])
        print(f"Gaudi len tokens: {len_g}, Xeon len tokens: {len_o}")
        print(f"Jaccard token overlap: {j:.3f}")
        print(f"Length ratio (Xeon/Gaudi): {len_ratio:.2f}\n")

        print("--- Gaudi completion ---")
        print(g["completion"][:600], "\n")

        print("--- Xeon OV completion ---")
        print(o["completion"][:600], "\n")

    if jaccs:
        avg_j = sum(jaccs) / len(jaccs)
        print("=" * 80)
        print(f"✅ Average Jaccard token overlap across {len(jaccs)} prompts: {avg_j:.3f}")
    else:
        print("❌ No shared IDs for comparison")

if __name__ == "__main__":
    main()
