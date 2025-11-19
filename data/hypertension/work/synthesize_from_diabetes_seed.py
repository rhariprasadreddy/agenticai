#!/usr/bin/env python3
import json
import re
from pathlib import Path

# ---------------------------------------------------------------------
# Paths
#   This file lives at: data/hypertension/work/synthesize_from_diabetes_seed.py
#   Repo root           = /home/agenticai/agenticai  -> parents[3]
# ---------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[3]

SEED_PATH = ROOT / "data/hypertension/work/from_diabetes_seed.jsonl"
OUT_PATH = ROOT / "data/hypertension/curated/train_htn_seed.jsonl"
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)


def build_messages_from_generic(rec: dict):
    """
    Try to recover a [system, user, assistant] style messages array
    from whatever the diabetes record has.
    """

    # Case 1: already in 'messages' format
    if "messages" in rec and isinstance(rec["messages"], list):
        msgs = rec["messages"]
        roles = {m.get("role") for m in msgs if isinstance(m, dict)}
        if "user" in roles and "assistant" in roles:
            return msgs

    # Case 2: alpaca-style: instruction / input / output
    instr = rec.get("instruction")
    output = rec.get("output")
    if instr and output:
        sys_msg = {
            "role": "system",
            "content": (
                "You are a hypertension diet assistant. "
                "Focus on low-sodium, heart-healthy meal planning, "
                "and mention sodium/blood-pressure in your reasoning."
            ),
        }
        user_msg = {"role": "user", "content": instr}
        asst_msg = {"role": "assistant", "content": output}
        return [sys_msg, user_msg, asst_msg]

    return None


def diabetes_to_htn_text(text: str) -> str:
    """
    Naive string-level conversion from diabetes-focused output
    to hypertension-focused output.
    """
    out = text

    # Focus shift: sugar ↔ BP/sodium
    replacements = [
        ("diabetes", "high blood pressure"),
        ("blood sugar", "blood pressure"),
        ("glucose", "blood pressure"),
        ("glycemic index", "sodium"),
        ("carb", "salt"),
        ("carbohydrate", "salt"),
        ("insulin", "blood pressure medication"),
    ]
    for a, b in replacements:
        out = re.sub(a, b, out, flags=re.IGNORECASE)

    # Ensure sodium / BP are mentioned at least once
    if "sodium" not in out.lower() and "salt" not in out.lower():
        out += "\nNote: This plan keeps overall salt/sodium intake in check to support blood pressure control."
    if "blood pressure" not in out.lower() and "bp" not in out.lower():
        out += "\nThis is aimed at gradual improvement in blood pressure (BP) over time."

    return out


def convert_record(rec: dict):
    msgs = build_messages_from_generic(rec)
    if not msgs:
        return None

    # system: override to HTN context
    new_msgs = []
    has_system = False
    for m in msgs:
        role = m.get("role")
        content = m.get("content", "")
        if role == "system":
            has_system = True
            new_msgs.append(
                {
                    "role": "system",
                    "content": (
                        "You are a hypertension diet assistant. "
                        "Follow DASH principles, keep sodium low, "
                        "and give short justifications mentioning salt and blood pressure."
                    ),
                }
            )
        elif role == "assistant":
            new_msgs.append(
                {
                    "role": "assistant",
                    "content": diabetes_to_htn_text(content),
                }
            )
        else:
            new_msgs.append(m)

    if not has_system:
        new_msgs.insert(
            0,
            {
                "role": "system",
                "content": (
                    "You are a hypertension diet assistant. "
                    "Follow DASH principles, keep sodium low, "
                    "and give short justifications mentioning salt and blood pressure."
                ),
            },
        )

    return {"messages": new_msgs}


def main():
    if not SEED_PATH.exists():
        print(f"❌ Seed file not found: {SEED_PATH}")
        return

    n_in = 0
    n_ok = 0

    with SEED_PATH.open() as fin, OUT_PATH.open("w") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            n_in += 1
            try:
                rec = json.loads(line)
            except Exception:
                continue

            new_rec = convert_record(rec)
            if not new_rec:
                continue

            fout.write(json.dumps(new_rec, ensure_ascii=False) + "\n")
            n_ok += 1

    print(
        f"🔹 Read {n_in} seed records, "
        f"wrote {n_ok} HTN records to {OUT_PATH}"
    )


if __name__ == "__main__":
    main()

