#!/usr/bin/env python3
import os
import re
from pathlib import Path
from typing import Optional

import numpy as np
from fastapi import FastAPI
from pydantic import BaseModel

from openvino import Core
from transformers import AutoTokenizer, AutoConfig

# -------------------------------------------------------------------
# Paths (inside container: /models is volume)
# -------------------------------------------------------------------
MERGED_DIR = Path(os.getenv("MERGED_DIR", "/models/diabetes_qwen_merged_fp16"))
OV_DIR = Path(os.getenv("OV_DIR", "/models/ov_diabetes_qwen_fp16"))

# Keep replies short by default
MAX_NEW_TOKENS_DEFAULT = int(os.getenv("MAX_NEW_TOKENS", "64"))

# Soft style hint to reduce rambling
ANSWER_SUFFIX = (
    "\n\nAnswer in 4–6 concise bullet points. "
    "Avoid repeating the same phrase multiple times."
)

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
core.set_property("CPU", {"INFERENCE_PRECISION_HINT": "bf16"})

compiled_model = core.compile_model(str(OV_DIR / "model_fp16.xml"), "CPU")
OUTPUT_PORT = compiled_model.output(0)

# -------------------------------------------------------------------
# Schemas
# -------------------------------------------------------------------
class GenerateRequest(BaseModel):
    prompt: str
    max_new_tokens: Optional[int] = None


class GenerateResponse(BaseModel):
    prompt: str
    completion: str
    num_tokens: int


# -------------------------------------------------------------------
# Helper: simple sentence de-dup and trimming
# -------------------------------------------------------------------
def clean_completion(completion: str, max_sentences: int = 6) -> str:
    # Split on sentence boundaries
    parts = re.split(r'(?<=[.!?])\s+', completion.strip())
    seen = set()
    out = []
    for s in parts:
        s_norm = s.strip().lower()
        if not s_norm:
            continue
        if s_norm in seen:
            continue  # drop exact repeats
        seen.add(s_norm)
        out.append(s.strip())
        if len(out) >= max_sentences:
            break
    return " ".join(out)


# -------------------------------------------------------------------
# Simple greedy generation
# -------------------------------------------------------------------
def greedy_generate_ov(prompt: str, max_new_tokens: int) -> str:
    # Add style hint for conciseness
    full_prompt = prompt + ANSWER_SUFFIX

    enc = tokenizer(full_prompt, return_tensors="np")
    input_ids = enc["input_ids"]
    attention_mask = enc["attention_mask"]

    for _ in range(max_new_tokens):
        res = compiled_model(
            {
                "input_ids": input_ids,
                "attention_mask": attention_mask,
            }
        )
        logits = res[OUTPUT_PORT]  # (1, seq_len, vocab_size)
        next_id = int(logits[0, -1].argmax())

        input_ids = np.concatenate([input_ids, [[next_id]]], axis=1)
        attention_mask = np.concatenate([attention_mask, [[1]]], axis=1)

        if EOS_ID is not None and next_id == EOS_ID:
            break

    full_text = tokenizer.decode(input_ids[0], skip_special_tokens=True)
    raw_completion = full_text[len(full_prompt):].strip()
    cleaned = clean_completion(raw_completion)
    return cleaned


# -------------------------------------------------------------------
# FastAPI app
# -------------------------------------------------------------------
app = FastAPI(title="Diabetes Qwen OpenVINO Service (Greedy + Clean)")


@app.get("/")
def root():
    return {"status": "ok", "model": "diabetes_qwen_ov_bf16_greedy_clean"}


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
