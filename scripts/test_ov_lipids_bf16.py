#!/usr/bin/env python3
from pathlib import Path

from optimum.intel.openvino import OVModelForCausalLM
from transformers import AutoTokenizer

# ROOT = /home/agenticai/agenticai
ROOT = Path(__file__).resolve().parents[1]
OV_DIR = (ROOT / "models" / "openvino" / "lipids" / "bf16").resolve()

print("🔹 Loading OV BF16 Lipids model from:", OV_DIR)

tokenizer = AutoTokenizer.from_pretrained(OV_DIR, use_fast=True)
model = OVModelForCausalLM.from_pretrained(
    OV_DIR,
    device="CPU",   # or "AUTO" if you enable GPU/iGPU in future
)

prompt = (
    "You are a lipids specialist dietitian.\n"
    "Patient: 58-year-old male, LDL 165 mg/dL, HDL 38 mg/dL, TG 210 mg/dL, "
    "hypertension controlled, no CKD.\n"
    "Give a one-day Indian diet plan focusing on LDL reduction and "
    "triglyceride control. Use bullet points only."
)

inputs = tokenizer(prompt, return_tensors="pt")
outputs = model.generate(
    **inputs,
    max_new_tokens=256,
    do_sample=False,
)
text = tokenizer.decode(outputs[0], skip_special_tokens=True)

print("====== OV LIPIDS OUTPUT ======")
print(text)
print("================================")

