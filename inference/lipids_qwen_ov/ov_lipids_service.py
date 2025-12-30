#!/usr/bin/env python3
import os
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI
from pydantic import BaseModel

from optimum.intel.openvino import OVModelForCausalLM
from transformers import AutoTokenizer

# Default to the path you just exported
OV_DIR = Path(
    os.getenv(
        "LIPIDS_OV_DIR",
        "/models/openvino/lipids/bf16",   # will be volume-mounted into container
    )
).resolve()

app = FastAPI(
    title="Lipids Diet OV Service",
    description="OpenVINO-based Lipids Specialist Agent (Qwen-LoRA merged, BF16)",
    version="1.0.0",
)

print(f"🔹 Loading Lipids OV model from: {OV_DIR}")
tokenizer = AutoTokenizer.from_pretrained(OV_DIR, use_fast=True)
model = OVModelForCausalLM.from_pretrained(OV_DIR, device="CPU")


class LipidsRequest(BaseModel):
    age: int
    sex: str
    ldl: float
    hdl: float
    tg: float
    comorbidities: List[str] = []
    notes: Optional[str] = None


class LipidsResponse(BaseModel):
    plan: str


def build_prompt(req: LipidsRequest) -> str:
    return (
        "You are a cardiometabolic lipids specialist dietitian.\n"
        f"Age: {req.age}, Sex: {req.sex}\n"
        f"LDL: {req.ldl} mg/dL, HDL: {req.hdl} mg/dL, TG: {req.tg} mg/dL\n"
        f"Comorbidities: {', '.join(req.comorbidities) or 'none'}\n"
        f"Extra notes: {req.notes or 'none'}\n\n"
        "Generate a concise 1-day Indian diet plan (breakfast, lunch, snacks, dinner) "
        "focused on LDL reduction and triglyceride control.\n"
        "- Use bullet points.\n"
        "- Prefer high-fiber, MUFA/PUFA fats, omega-3 rich foods.\n"
        "- Avoid deep-fried foods, high-sugar desserts, and trans fats.\n"
        "- Keep the response under 350 words.\n"
    )


@app.post("/v1/lipids/plan", response_model=LipidsResponse)
def lipids_plan(req: LipidsRequest) -> LipidsResponse:
    prompt = build_prompt(req)
    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = model.generate(
        **inputs,
        max_new_tokens=384,
        do_sample=False,  # deterministic, good for clinical auditing
    )
    text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return LipidsResponse(plan=text)


@app.get("/healthz")
def healthz():
    return {"status": "ok", "model_path": str(OV_DIR)}

