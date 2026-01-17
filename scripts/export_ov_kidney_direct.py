#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
export_ov_kidney_direct.py

Export merged HF kidney Qwen model to OpenVINO BF16, similar to HTN/lipids flow.

Assumes:
  - HF merged model dir: /home/agenticai/agenticai/models/qwen2.5-1.5b-kidney-merged
  - Output OV dir:        /home/agenticai/agenticai/models/qwen2.5-1.5b-kidney-ov
  - Running inside ov120 venv with openvino + optimum-intel installed.
"""

import os
from pathlib import Path

from optimum.intel.openvino import OVModelForCausalLM
from transformers import AutoTokenizer

ROOT = Path(__file__).resolve().parents[1]

HF_MERGED_DIR = os.getenv(
    "KIDNEY_HF_DIR",
    str(ROOT / "models" / "qwen2.5-1.5b-kidney-merged"),
)

OV_OUT_DIR = os.getenv(
    "KIDNEY_OV_DIR",
    str(ROOT / "models" / "qwen2.5-1.5b-kidney-ov"),
)

hf_dir = Path(HF_MERGED_DIR)
ov_dir = Path(OV_OUT_DIR)

assert hf_dir.is_dir(), f"❌ HF merged kidney model dir not found: {hf_dir}"
ov_dir.mkdir(parents=True, exist_ok=True)

print(f"✅ Exporting HF kidney model from: {hf_dir}")
print(f"✅ Target OpenVINO BF16 dir:       {ov_dir}")

ov_model = OVModelForCausalLM.from_pretrained(
    hf_dir,
    export=True,
    ov_config={
        "INFERENCE_PRECISION_HINT": "bf16",
        "PERFORMANCE_HINT": "LATENCY",
    },
)
ov_model.save_pretrained(ov_dir)

tok = AutoTokenizer.from_pretrained(hf_dir)
tok.save_pretrained(ov_dir)

print("✅ OpenVINO BF16 kidney model saved to:", ov_dir)
