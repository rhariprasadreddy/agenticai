#!/usr/bin/env python3
import os
from pathlib import Path

import numpy as np
from openvino import Core
from transformers import AutoTokenizer, AutoConfig

# -------------------------------------------------------------------
# Paths (Xeon server)
# -------------------------------------------------------------------
MERGED_DIR = Path(os.getenv("MERGED_DIR", "/home/agenticai/agenticai/models/hypertension_qwen_merged_fp16"))
OV_DIR     = Path(os.getenv("OV_DIR",     "/home/agenticai/models/hypertension_qwen_ov"))

print(f"🔹 Using HF merged dir: {MERGED_DIR}")
print(f"🔹 Using OV IR dir   : {OV_DIR}")

if not MERGED_DIR.is_dir():
    raise SystemExit(f"❌ MERGED_DIR not found: {MERGED_DIR}")
if not (OV_DIR / "model_fp16.xml").is_file():
    raise SystemExit(f"❌ OV model_fp16.xml not found in {OV_DIR}")

# -------------------------------------------------------------------
# Load tokenizer & config from merged HF model
# -------------------------------------------------------------------
print("🔹 Loading tokenizer & config...")
tok = AutoTokenizer.from_pretrained(
    str(MERGED_DIR),
    use_fast=True,
    local_files_only=True,
    trust_remote_code=True,
)
cfg = AutoConfig.from_pretrained(
    str(MERGED_DIR),
    local_files_only=True,
    trust_remote_code=True,
)
EOS_ID = cfg.eos_token_id or tok.eos_token_id

# -------------------------------------------------------------------
# Load OpenVINO model with BF16 hint on Xeon
# -------------------------------------------------------------------
print("🔹 Loading OpenVINO model (BF16 hint)...")
core = Core()
core.set_property("CPU", {"INFERENCE_PRECISION_HINT": "bf16"})
compiled_model = core.compile_model(str(OV_DIR / "model_fp16.xml"), "CPU")
OUTPUT_PORT = compiled_model.output(0)

# -------------------------------------------------------------------
# Simple greedy generation (same pattern as diabetes tester)
# -------------------------------------------------------------------
def greedy_generate_ov(prompt: str, max_new_tokens: int = 80) -> str:
    enc = tok(prompt, return_tensors="np")
    input_ids = enc["input_ids"]          # (1, T)
    attention_mask = enc["attention_mask"]

    for _ in range(max_new_tokens):
        res = compiled_model(
            {
                "input_ids": input_ids,
                "attention_mask": attention_mask,
            }
        )
        logits = res[OUTPUT_PORT]         # (1, seq_len, vocab_size)
        next_id = int(logits[0, -1].argmax())

        # append token
        input_ids = np.concatenate([input_ids, [[next_id]]], axis=1)
        attention_mask = np.concatenate([attention_mask, [[1]]], axis=1)

        if EOS_ID is not None and next_id == EOS_ID:
            break

    full_text = tok.decode(input_ids[0], skip_special_tokens=True)
    completion = full_text[len(prompt):].strip()
    return completion

# -------------------------------------------------------------------
# Main: test a hypertension-style prompt
# -------------------------------------------------------------------
if __name__ == "__main__":
    prompt = (
        "Suggest a one-day low-sodium diet plan for an adult with hypertension "
        "who walks 30 minutes a day. Be concise and practical."
    )
    print("=== PROMPT ===")
    print(prompt)
    print("🔹 Running greedy generation with OpenVINO BF16...\n")

    completion = greedy_generate_ov(prompt, max_new_tokens=96)

    print("=== COMPLETION (BF16) ===")
    print(completion[:800])
