#!/usr/bin/env python3
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel

from optimum.intel.openvino import OVModelForCausalLM
from transformers import AutoTokenizer

# -------------------------------------------------------------------
# Config: Standardized Path
# -------------------------------------------------------------------
model_path = os.getenv("MODEL_DIR", "/model")

app = FastAPI(
    title="Hypertension Qwen OV Service",
    description="OpenVINO-based Hypertension Specialist Agent (Optimum)",
    version="2.0.0",
)

print(f"🔹 Loading Hypertension OV model from: {model_path}")
# Load Tokenizer
tokenizer = AutoTokenizer.from_pretrained(model_path, use_fast=True)

# Load Model using Optimum (Auto-handles the KV Cache state issues)
model = OVModelForCausalLM.from_pretrained(
    model_path, 
    device="CPU",
    ov_config={"INFERENCE_PRECISION_HINT": "bf16"}
)

# -------------------------------------------------------------------
# Schemas
# -------------------------------------------------------------------
class GenerateRequest(BaseModel):
    prompt: str
    max_new_tokens: int = 256
    temperature: float = 0.1
    top_p: float = 0.9

class GenerateResponse(BaseModel):
    completion: str

# -------------------------------------------------------------------
# Routes
# -------------------------------------------------------------------
@app.get("/healthz")
def healthz():
    return {"status": "ok", "model_path": str(model_path)}

@app.post("/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest):
    # 1. Tokenize
    inputs = tokenizer(req.prompt, return_tensors="pt")
    
    # 2. Generate (Optimum handles the loop and state)
    outputs = model.generate(
        **inputs,
        max_new_tokens=req.max_new_tokens,
        temperature=req.temperature,
        top_p=req.top_p,
        do_sample=req.temperature > 0.0,
        repetition_penalty=1.1,
    )
    
    # 3. Decode
    text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    # 4. Clean Output (Remove original prompt if echoed)
    response_text = text[len(req.prompt):] if text.startswith(req.prompt) else text
    
    return GenerateResponse(completion=response_text)