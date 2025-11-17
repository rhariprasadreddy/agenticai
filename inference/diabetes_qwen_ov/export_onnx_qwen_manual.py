#!/usr/bin/env python3
import os
from pathlib import Path

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

MERGED_DIR = Path("/home/agenticai/agenticai/models/diabetes_qwen_merged_fp16")
OUT_DIR    = Path("/home/agenticai/agenticai/models/onnx_qwen")
OUT_DIR.mkdir(parents=True, exist_ok=True)

print(f"✅ Using merged model from: {MERGED_DIR}")

# 1) Load tokenizer & model from local disk
tokenizer = AutoTokenizer.from_pretrained(
    str(MERGED_DIR),
    use_fast=True,
    local_files_only=True,
    trust_remote_code=True,
)
model = AutoModelForCausalLM.from_pretrained(
    str(MERGED_DIR),
    local_files_only=True,
    trust_remote_code=True,
)

# For CPU export, stay in FP32
model = model.to(torch.float32).to("cpu")
model.config.use_cache = False
model.eval()

# 2) Build a dummy input (batch=1, some prompt) to trace the graph
dummy = tokenizer(
    "Hello, this is a diabetes coaching test prompt.",
    return_tensors="pt",
)
input_ids      = dummy["input_ids"].to("cpu")
attention_mask = dummy["attention_mask"].to("cpu")

print("🔹 dummy input_ids shape:", input_ids.shape)
print("🔹 dummy attention_mask shape:", attention_mask.shape)

# 3) ONNX export
onnx_path = OUT_DIR / "model.onnx"
print("🔁 Exporting to:", onnx_path)

torch.onnx.export(
    model,
    (input_ids, attention_mask),
    str(onnx_path),
    input_names=["input_ids", "attention_mask"],
    output_names=["logits"],
    dynamic_axes={
        "input_ids": {0: "batch", 1: "sequence"},
        "attention_mask": {0: "batch", 1: "sequence"},
        "logits": {0: "batch", 1: "sequence"},
    },
    do_constant_folding=True,
    opset_version=14,
)

print("✅ ONNX exported to", onnx_path)
