#!/usr/bin/env python3
from pathlib import Path
import numpy as np

from openvino import Core
from transformers import AutoTokenizer, AutoConfig

MERGED = Path("/home/agenticai/agenticai/models/diabetes_qwen_merged_fp16")
OV_DIR = Path("/home/agenticai/agenticai/models/ov_diabetes_qwen_fp16")

# 1) Tokenizer + config from merged HF model
print("🔹 Loading tokenizer & config...")
tok = AutoTokenizer.from_pretrained(
    str(MERGED),
    use_fast=True,
    local_files_only=True,
    trust_remote_code=True,
)
config = AutoConfig.from_pretrained(
    str(MERGED),
    local_files_only=True,
    trust_remote_code=True,
)

eos_id = config.eos_token_id or tok.eos_token_id

# 2) OpenVINO BF16 / AMX load
print("🔹 Loading OpenVINO model (BF16 hint)...")
core = Core()

# Ask CPU plugin to run in BF16 where possible (this is where AMX BF16 kicks in)
core.set_property("CPU", {
    "INFERENCE_PRECISION_HINT": "bf16"
})

compiled_model = core.compile_model(str(OV_DIR / "model_fp16.xml"), "CPU")
output = compiled_model.output(0)

# 3) Prompt
prompt = (
    "Suggest a daily diet plan for an adult with type-2 diabetes "
    "who does moderate exercise. Be concise and practical."
)
print("=== PROMPT ===")
print(prompt)

enc = tok(prompt, return_tensors="np")
input_ids = enc["input_ids"]
attention_mask = enc["attention_mask"]

# 4) Greedy decode loop (no KV cache, short answer is fine)
max_new_tokens = 64
print("🔹 Running greedy generation with OpenVINO BF16...")
for step in range(max_new_tokens):
    res = compiled_model(
        {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
        }
    )
    logits = res[output]   # (1, T, vocab)
    next_id = int(logits[0, -1].argmax())
    input_ids = np.concatenate([input_ids, [[next_id]]], axis=1)
    attention_mask = np.concatenate([attention_mask, [[1]]], axis=1)
    if eos_id is not None and next_id == eos_id:
        print(f"🔹 Stopped at step {step+1} on EOS")
        break

full_text = tok.decode(input_ids[0], skip_special_tokens=True)
completion = full_text[len(prompt):].strip()

print("\n=== COMPLETION (BF16) ===")
print(completion)
