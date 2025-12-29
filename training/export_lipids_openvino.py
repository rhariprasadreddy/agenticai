#!/usr/bin/env python3
import os
from pathlib import Path

from optimum.intel.openvino import OVModelForCausalLM
from transformers import AutoTokenizer

# Project root = parent of this file: /home/agenticai/agenticai
ROOT = Path(__file__).resolve().parents[1]

MERGED_DIR = Path(
    os.getenv(
        "LIPIDS_MERGED_DIR",
        ROOT / "models/lipids_qwen_merged_fp16",
    )
).resolve()

OV_FP16_DIR = Path(
    os.getenv(
        "LIPIDS_OV_FP16_DIR",
        ROOT / "models/openvino/lipids/fp16",
    )
).resolve()

OV_BF16_DIR = Path(
    os.getenv(
        "LIPIDS_OV_BF16_DIR",
        ROOT / "models/openvino/lipids/bf16",
    )
).resolve()

OV_FP16_DIR.mkdir(parents=True, exist_ok=True)
OV_BF16_DIR.mkdir(parents=True, exist_ok=True)

print("🔹 Merged HF model :", MERGED_DIR)
print("🔹 OV FP16 out     :", OV_FP16_DIR)
print("🔹 OV BF16 out     :", OV_BF16_DIR)

assert (MERGED_DIR / "config.json").is_file(), "❌ config.json missing in merged dir"

# Shared tokenizer
tokenizer = AutoTokenizer.from_pretrained(MERGED_DIR, use_fast=True)
tokenizer.save_pretrained(OV_FP16_DIR)
tokenizer.save_pretrained(OV_BF16_DIR)

# ---- FP16 export ----
print("🔹 Exporting FP16 OpenVINO IR...")
ov_model_fp16 = OVModelForCausalLM.from_pretrained(
    MERGED_DIR,
    export=True,
    compile=False,
    ov_config={"INFERENCE_PRECISION_HINT": "f16"},
)
ov_model_fp16.save_pretrained(OV_FP16_DIR)
print("✅ Saved FP16 IR at:", OV_FP16_DIR)

# ---- BF16 export ----
print("🔹 Exporting BF16 OpenVINO IR...")
ov_model_bf16 = OVModelForCausalLM.from_pretrained(
    MERGED_DIR,
    export=True,
    compile=False,
    ov_config={"INFERENCE_PRECISION_HINT": "bf16"},
)
ov_model_bf16.save_pretrained(OV_BF16_DIR)
print("✅ Saved BF16 IR at:", OV_BF16_DIR)

