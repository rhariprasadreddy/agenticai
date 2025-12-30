#!/usr/bin/env python3
import os
import torch
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from optimum.intel.openvino import OVModelForCausalLM
from transformers import AutoTokenizer

# Standardize path
OV_DIR = Path(os.getenv("BASE_MODEL_DIR", "/model")).resolve()

app = FastAPI(title="Diabetes Specialist", version="1.0.0")

print(f"🔹 Loading Diabetes Model from: {OV_DIR}")

try:
    tokenizer = AutoTokenizer.from_pretrained(OV_DIR, trust_remote_code=True)
    # optimum-intel handles the heavy lifting (Stateful/KV-Cache handled internally)
    model = OVModelForCausalLM.from_pretrained(
        OV_DIR, 
        device="CPU", 
        ov_config={"PERFORMANCE_HINT": "LATENCY"},
        trust_remote_code=True
    )
except Exception as e:
    print(f"❌ Error loading model: {e}")
    model = None

class Request(BaseModel):
    prompt: str
    max_new_tokens: int = 350

class Response(BaseModel):
    reply: str
    provider: str = "diabetes_qwen_ov"
    specialized: bool = True

@app.post("/generate", response_model=Response)
def generate(req: Request):
    if not model: raise HTTPException(500, "Model loading failed")

    # 1. Structure the prompt
    system_instruction = (
        "You are a helpful diabetes specialist dietitian. "
        "Create a 1-day Indian vegetarian meal plan. "
        "Make options practical. Use bullet points."
    )

    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": req.prompt}
    ]
    
    # 2. Apply Chat Template
    formatted_prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(formatted_prompt, return_tensors="pt")

    # 3. Generate
    outputs = model.generate(
        **inputs,
        max_new_tokens=req.max_new_tokens,
        temperature=0.2,       
        do_sample=True,
        repetition_penalty=1.1
    )

    # 4. SLICING (The Critical Fix)
    # The model returns [Prompt Tokens] + [Answer Tokens]
    # We must cut off the Prompt Tokens so the Gateway doesn't get confused.
    input_length = inputs.input_ids.shape[1]
    generated_tokens = outputs[0][input_length:]

    # 5. Decode only the new part
    reply = tokenizer.decode(generated_tokens, skip_special_tokens=True).strip()

    return Response(reply=reply)
