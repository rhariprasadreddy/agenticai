#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel

from optimum.intel.openvino import OVModelForCausalLM
from transformers import AutoTokenizer


# ----------------------------------------------------------------------
# Config: where the OpenVINO kidney model lives in the container
# ----------------------------------------------------------------------
# On the host you have:
#   /home/agenticai/agenticai/models/qwen2.5-1.5b-kidney-ov
# We will mount that into the container at /models/qwen2.5-1.5b-kidney-ov
# and refer to it via KIDNEY_MODEL_DIR.
# ----------------------------------------------------------------------

MODEL_DIR = Path(
    os.getenv(
        "KIDNEY_MODEL_DIR",
        "/models/qwen2.5-1.5b-kidney-ov",
    )
).resolve()

print(f"🔹 Starting Kidney OV service. MODEL_DIR = {MODEL_DIR}")

if not MODEL_DIR.is_dir():
    raise RuntimeError(f"❌ Kidney OV model directory not found: {MODEL_DIR}")

# ----------------------------------------------------------------------
# Load tokenizer + OV model at startup
# ----------------------------------------------------------------------
tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR, use_fast=True)
model = OVModelForCausalLM.from_pretrained(
    MODEL_DIR,
    device="CPU",  # Xeon CPU inference
)

# ----------------------------------------------------------------------
# FastAPI app and request/response schema
# ----------------------------------------------------------------------
app = FastAPI(title="Kidney Qwen OV Service", version="1.0.0")


class GenerateRequest(BaseModel):
    prompt: str
    max_new_tokens: int = 200
    temperature: float = 0.0
    top_p: float = 1.0
    top_k: int = 0


class GenerateResponse(BaseModel):
    output: str


# ----------------------------------------------------------------------
# Utility: build a safe renal system prompt
# ----------------------------------------------------------------------
RENAL_SYSTEM_PROMPT = (
    "You are a conservative renal dietitian for CKD patients in India. "
    "You focus on diet, potassium, phosphorus, sodium, protein, and fluids. "
    "You always recommend that the patient discuss final decisions with "
    "their nephrologist or treating doctor. Avoid making medication or "
    "dialysis prescriptions."
)


def build_full_prompt(user_prompt: str) -> str:
    return f"{RENAL_SYSTEM_PROMPT}\n\nPatient: {user_prompt.strip()}\nDietitian:"


# ----------------------------------------------------------------------
# Routes
# ----------------------------------------------------------------------
@app.get("/healthz")
def healthz():
    return {"status": "ok", "model_dir": str(MODEL_DIR)}


@app.post("/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest):
    full_prompt = build_full_prompt(req.prompt)

    inputs = tokenizer(full_prompt, return_tensors="pt")

    # OpenVINO backend ignores some sampling params, but we pass them anyway
    outputs = model.generate(
        **inputs,
        max_new_tokens=req.max_new_tokens,
        do_sample=req.temperature > 0.0,
    )

    text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return GenerateResponse(output=text)


