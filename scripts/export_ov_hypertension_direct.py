#!/usr/bin/env python3
import os
from pathlib import Path

import torch
import openvino as ov
from transformers import AutoTokenizer, AutoModelForCausalLM, AutoConfig

# -------------------------------------------------------------------
# Paths
# -------------------------------------------------------------------
MERGED_DIR = Path("/home/agenticai/agenticai/models/hypertension_qwen_merged_fp16")
OV_DIR     = Path("/home/agenticai/models/hypertension_qwen_ov")

OV_DIR.mkdir(parents=True, exist_ok=True)

if not MERGED_DIR.is_dir():
    raise SystemExit(f"❌ MERGED_DIR not found: {MERGED_DIR}")

print("🔹 Using merged HF model from:", MERGED_DIR)
print("🔹 Output OV IR dir         :", OV_DIR)

# -------------------------------------------------------------------
# Load tokenizer & base model
# -------------------------------------------------------------------
print("🔹 Loading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(
    str(MERGED_DIR),
    use_fast=True,
    trust_remote_code=True,
    local_files_only=True,
)

print("🔹 Loading HF CausalLM model (FP16)...")
base_model = AutoModelForCausalLM.from_pretrained(
    str(MERGED_DIR),
    torch_dtype=torch.float16,
    trust_remote_code=True,
    local_files_only=True,
)
base_model.eval()

# Make sure we don't use KV cache / extra outputs during export
if hasattr(base_model.config, "use_cache"):
    base_model.config.use_cache = False

# -------------------------------------------------------------------
# Wrapper: force clean signature & output
# -------------------------------------------------------------------
class QwenCausalWrapper(torch.nn.Module):
    """
    Wrap Qwen CausalLM so that:
      forward(input_ids, attention_mask) -> logits (Tensor)
    No past_key_values, no dict outputs. This keeps the tracer happy.
    """
    def __init__(self, model):
        super().__init__()
        self.model = model

    def forward(self, input_ids, attention_mask=None):
        out = self.model(
            input_ids=input_ids,
            attention_mask=attention_mask,
            use_cache=False,
            output_attentions=False,
            output_hidden_states=False,
            return_dict=True,
        )
        return out.logits   # (batch, seq, vocab)

wrapped_model = QwenCausalWrapper(base_model)
wrapped_model.eval()

# -------------------------------------------------------------------
# Dummy example input for conversion
# -------------------------------------------------------------------
print("🔹 Preparing dummy input...")
seq_len = 16
dummy_input_ids = torch.ones((1, seq_len), dtype=torch.long)
dummy_attention = torch.ones_like(dummy_input_ids)

example_input = (dummy_input_ids, dummy_attention)

# -------------------------------------------------------------------
# OpenVINO conversion
# -------------------------------------------------------------------
print("🔹 Converting wrapped HF model → OpenVINO IR (this may take a while)...")
ov_model = ov.convert_model(
    wrapped_model,
    example_input=example_input,
)

out_xml = OV_DIR / "model_fp16.xml"
print(f"🔹 Saving IR to: {out_xml}")
ov.save_model(ov_model, str(out_xml))

print("✅ Done. OV model saved at:", out_xml)
