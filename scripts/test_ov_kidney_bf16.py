#!/usr/bin/env python3
from pathlib import Path

from optimum.intel.openvino import OVModelForCausalLM
from transformers import AutoTokenizer


# ---------------------------------------------------------------------
# Adjust paths for kidney
# HF merged model was exported to:
#   /home/agenticai/agenticai/models/qwen2.5-1.5b-kidney-ov
# ---------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]
OV_DIR = ROOT / "models" / "qwen2.5-1.5b-kidney-ov"

print("🔹 Loading OV BF16 Kidney model from:", OV_DIR)

# ---------------------------------------------------------------------
# Load tokenizer + OpenVINO model
# ---------------------------------------------------------------------
tokenizer = AutoTokenizer.from_pretrained(OV_DIR, use_fast=True)

model = OVModelForCausalLM.from_pretrained(
    OV_DIR,
    device="CPU",       # Xeon inference
)

# ---------------------------------------------------------------------
# Kidney test prompt (CKD diet domain)
# ---------------------------------------------------------------------
prompt = (
    "You are a renal dietitian specializing in CKD.\n"
    "Patient: 55-year-old, CKD stage 3, potassium slightly elevated.\n"
    "Question: I eat a lot of tomatoes every day. Is this okay?\n"
    "Give a short, safe, Indian dietary explanation."
)

# ---------------------------------------------------------------------
# Tokenize, generate, decode
# ---------------------------------------------------------------------
inputs = tokenizer(prompt, return_tensors="pt")

outputs = model.generate(
    **inputs,
    max_new_tokens=200,
    do_sample=False,   # deterministic test
)

text = tokenizer.decode(outputs[0], skip_special_tokens=True)

# ---------------------------------------------------------------------
# Print final result
# ---------------------------------------------------------------------
print("====== OV KIDNEY OUTPUT ======")
print(text)
print("================================")

