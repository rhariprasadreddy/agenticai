#!/usr/bin/env python3
import json
from pathlib import Path

import torch
from optimum.intel.openvino import OVModelForCausalLM
from transformers import AutoTokenizer, AutoModelForCausalLM

ROOT = Path(__file__).resolve().parents[1]

HF_DIR = (ROOT / "models" / "lipids_qwen_merged_fp16").resolve()
OV_DIR = (ROOT / "models" / "openvino" / "lipids" / "bf16").resolve()
VAL_PATH = (ROOT / "data" / "lipids" / "curated" / "val.jsonl").resolve()

print("🔹 HF merged model :", HF_DIR)
print("🔹 OV BF16 model   :", OV_DIR)
print("🔹 Val file        :", VAL_PATH)

# --- load tokenizer once ---
tokenizer = AutoTokenizer.from_pretrained(HF_DIR, use_fast=True)

# --- load HF model on CPU, no accelerate/device_map ---
hf_model = AutoModelForCausalLM.from_pretrained(
    HF_DIR,
    torch_dtype=torch.float16,   # fp16 weights, OK on Xeon RAM
)
hf_model.to("cpu")
hf_model.eval()

# --- load OV model ---
ov_model = OVModelForCausalLM.from_pretrained(
    OV_DIR,
    device="CPU",
)

def to_prompt(rec):
    """Turn a SFT record into a plain text prompt."""
    if "messages" in rec:
        parts = []
        for m in rec["messages"]:
            if m.get("role") == "user":
                parts.append(m.get("content", ""))
        return "\n".join(parts)
    if "text" in rec:
        return rec["text"]
    return json.dumps(rec, ensure_ascii=False)

# --- load a few validation samples ---
samples = []
with VAL_PATH.open() as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        samples.append(json.loads(line))

print(f"🔹 Loaded {len(samples)} val samples.")
samples = samples[:2]  # keep it light

def generate_hf(prompt: str) -> str:
    inputs = tokenizer(prompt, return_tensors="pt")
    with torch.no_grad():
        out = hf_model.generate(
            **inputs,
            max_new_tokens=128,
            do_sample=False,
        )
    return tokenizer.decode(out[0], skip_special_tokens=True)

def generate_ov(prompt: str) -> str:
    inputs = tokenizer(prompt, return_tensors="pt")
    out = ov_model.generate(
        **inputs,
        max_new_tokens=128,
        do_sample=False,
    )
    return tokenizer.decode(out[0], skip_special_tokens=True)

for i, rec in enumerate(samples, start=1):
    prompt = to_prompt(rec)
    print("\n" + "=" * 80)
    print(f"🧪 SAMPLE {i} PROMPT:")
    print(prompt)
    print("-" * 80)

    hf_out = generate_hf(prompt)
    ov_out = generate_ov(prompt)

    print("🤖 HF MERGED OUTPUT:")
    print(hf_out)
    print("-" * 80)
    print("🧠 OV BF16 OUTPUT:")
    print(ov_out)
    print("=" * 80)

