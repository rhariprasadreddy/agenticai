#!/usr/bin/env python3
# Merge Diabetes LoRA adapters into a full FP16 Qwen2.5 model

import os
from pathlib import Path

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

BASE_MODEL = os.getenv("DIAB_BASE_MODEL", "/workspace/.hf/models/qwen2.5-1.5b-instruct")
LORA_DIR   = os.getenv("DIAB_LORA_DIR", "/workspace/models/diabetes_qwen_lora")
OUT_DIR    = os.getenv("DIAB_MERGED_DIR", "/workspace/models/diabetes_qwen_merged_fp16")

BASE_MODEL = str(Path(BASE_MODEL).resolve())
LORA_DIR   = str(Path(LORA_DIR).resolve())
OUT_DIR    = str(Path(OUT_DIR).resolve())
Path(OUT_DIR).mkdir(parents=True, exist_ok=True)

print("🔹 Base model dir :", BASE_MODEL)
print("🔹 LoRA dir       :", LORA_DIR)
print("🔹 Out (merged)   :", OUT_DIR)

assert Path(BASE_MODEL, "config.json").is_file(), f"❌ No config.json in {BASE_MODEL}"
assert Path(LORA_DIR, "adapter_config.json").is_file(), \
       f"❌ No adapter_config.json in {LORA_DIR}"

# 1) Load base
print("🔹 Loading base model...")
base = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    torch_dtype=torch.float16,
    local_files_only=True,
)

# 2) Attach LoRA
print("🔹 Attaching LoRA adapters...")
model = PeftModel.from_pretrained(
    base,
    LORA_DIR,
    local_files_only=True,
)

# 3) Merge & unload
print("🔹 Merging LoRA into base (FP16)...")
model = model.merge_and_unload()
model.eval()

# 4) Save merged HF model
print("🔹 Saving merged model to:", OUT_DIR)
model.save_pretrained(OUT_DIR)

# 5) Save tokenizer from the LoRA dir (it has your special tokens if any)
print("🔹 Saving tokenizer...")
tok = AutoTokenizer.from_pretrained(
    LORA_DIR,
    use_fast=True,
    local_files_only=True,
)
tok.save_pretrained(OUT_DIR)

print("✅ Done. Merged Diabetes Qwen model at:", OUT_DIR)

