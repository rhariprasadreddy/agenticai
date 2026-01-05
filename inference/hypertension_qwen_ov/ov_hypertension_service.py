#!/usr/bin/env python3
import os
from pathlib import Path
from typing import Optional

import numpy as np
from fastapi import FastAPI
from pydantic import BaseModel

from openvino import Core
from transformers import AutoTokenizer, AutoConfig

# -------------------------------------------------------------------
# Paths (inside container: /models is volume)
# We'll bind:
#   /home/agenticai/agenticai/models/hypertension_qwen_merged_fp16 -> /models/hypertension_qwen_merged_fp16
#   /home/agenticai/models/hypertension_qwen_ov                    -> /models/hypertension_qwen_ov
# -------------------------------------------------------------------
MERGED_DIR = Path(os.getenv("MERGED_DIR", "/models/hypertension_qwen_merged_fp16"))
OV_DIR     = Path(os.getenv("OV_DIR", "/models/hypertension_qwen_ov"))

MAX_NEW_TOKENS_DEFAULT = int(os.getenv("MAX_NEW_TOKENS", "80"))

print("🔹 Loading tokenizer & config from:", MERGED_DIR)
tokenizer = AutoTokenizer.from_pretrained(
    str(MERGED_DIR),
    use_fast=True,
    local_files_only=True,
    trust_remote_code=True,
)
config = AutoConfig.from_pretrained(
    str(MERGED_DIR),
    local_files_only=True,
    trust_remote_code=True,
)
EOS_ID = config.eos_token_id or tokenizer.eos_token_id

print("🔹 Loading OpenVINO model from:", OV_DIR)
core = Core()
# Hint BF16 on Xeon
core.set_property("CPU", {"INFERENCE_PRECISION_HINT": "bf16"})

compiled_model = core.compile_model(str(OV_DIR / "model_fp16.xml"), "CPU")
OUTPUT_PORT = compiled_model.output(0)

# -------------------------------------------------------------------
# Request / Response schemas
# -------------------------------------------------------------------
class GenerateRequest(BaseModel):
    prompt: str
    max_new_tokens: Optional[int] = None


class GenerateResponse(BaseModel):
    prompt: str
    completion: str
    num_tokens: int


# -------------------------------------------------------------------
# Simple greedy generation – same logic as test_ov_htn_bf16.py
# -------------------------------------------------------------------
def greedy_generate_ov(prompt: str, max_new_tokens: int) -> str:
    enc = tokenizer(prompt, return_tensors="np")
    input_ids = enc["input_ids"]          # (1, T)
    attention_mask = enc["attention_mask"]

    for _ in range(max_new_tokens):
        res = compiled_model(
            {
                "input_ids": input_ids,
                "attention_mask": attention_mask,
            }
        )
        logits = res[OUTPUT_PORT]         # (1, seq_len, vocab_size)
        next_id = int(logits[0, -1].argmax())

        # append token
        input_ids = np.concatenate([input_ids, [[next_id]]], axis=1)
        attention_mask = np.concatenate([attention_mask, [[1]]], axis=1)

        if EOS_ID is not None and next_id == EOS_ID:
            break

    full_text = tokenizer.decode(input_ids[0], skip_special_tokens=True)
    completion = full_text[len(prompt):].strip()
    return completion


# -------------------------------------------------------------------
# FastAPI app
# -------------------------------------------------------------------
app = FastAPI(title="Hypertension Qwen OpenVINO Service (Greedy BF16)")


@app.get("/")
def root():
    return {"status": "ok", "model": "hypertension_qwen_ov_bf16_greedy"}


@app.post("/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest):
    max_new = req.max_new_tokens or MAX_NEW_TOKENS_DEFAULT
    completion = greedy_generate_ov(req.prompt, max_new_tokens=max_new)
    num_tokens = len(tokenizer.encode(completion))

    return GenerateResponse(
        prompt=req.prompt,
        completion=completion,
        num_tokens=num_tokens,
    )
