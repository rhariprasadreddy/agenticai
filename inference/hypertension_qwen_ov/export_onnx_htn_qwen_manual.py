#!/usr/bin/env python3
import os
from pathlib import Path

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

# Paths
MERGED_DIR = Path(
    os.getenv(
        "HTN_MERGED_DIR",
        "/home/agenticai/agenticai/models/hypertension_qwen_merged_fp16",
    )
)
ONNX_DIR = Path(
    os.getenv(
        "HTN_ONNX_DIR",
        "/home/agenticai/agenticai/models/onnx_hypertension_qwen",
    )
)
ONNX_DIR.mkdir(parents=True, exist_ok=True)
ONNX_PATH = ONNX_DIR / "model.onnx"

print("🔹 Using merged HF model :", MERGED_DIR)
print("🔹 ONNX output directory :", ONNX_DIR)

assert MERGED_DIR.is_dir(), f"❌ Merged dir not found: {MERGED_DIR}"

print("🔹 Loading tokenizer & model...")
tok = AutoTokenizer.from_pretrained(
    str(MERGED_DIR),
    use_fast=True,
    local_files_only=True,
    trust_remote_code=True,
)
model = AutoModelForCausalLM.from_pretrained(
    str(MERGED_DIR),
    torch_dtype=torch.float16,
    local_files_only=True,
    trust_remote_code=True,
)
model.eval()
model.to("cpu")

class QwenForONNX(torch.nn.Module):
    def __init__(self, model):
        super().__init__()
        self.model = model

    def forward(self, input_ids, attention_mask=None):
        out = self.model(input_ids=input_ids, attention_mask=attention_mask)
        return out.logits

wrapper = QwenForONNX(model).eval()

# Simple nominal length; we'll use dynamic axes anyway
seq_len = 128
dummy_ids = torch.ones((1, seq_len), dtype=torch.long)
dummy_mask = torch.ones((1, seq_len), dtype=torch.long)

print("🔹 Exporting to ONNX:", ONNX_PATH)
torch.onnx.export(
    wrapper,
    (dummy_ids, dummy_mask),
    str(ONNX_PATH),
    input_names=["input_ids", "attention_mask"],
    output_names=["logits"],
    opset_version=14,
    do_constant_folding=True,
    dynamic_axes={
        "input_ids": {0: "batch", 1: "seq"},
        "attention_mask": {0: "batch", 1: "seq"},
        "logits": {0: "batch", 1: "seq"},
    },
)

print("✅ ONNX export done:", ONNX_PATH)
