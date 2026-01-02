#!/usr/bin/env python3
import json
from pathlib import Path

import numpy as np
from openvino import Core
from transformers import AutoTokenizer, AutoConfig

PROMPTS = ROOT / "eval/prompts_hypertension.txt")
OUT = ROOT / "eval/ov_htn_outputs.jsonl")

MERGED_DIR = ROOT / "models/hypertension_qwen_merged_fp16")
OV_DIR     = Path("/home/agenticai/models/hypertension_qwen_ov")

def load_prompts(path: Path):
    prompts = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            prompts.append(line)
    return prompts

def main():
    print(f"🔹 Using HF merged dir: {MERGED_DIR}")
    print(f"🔹 Using OV IR dir   : {OV_DIR}")

    if not MERGED_DIR.is_dir():
        raise SystemExit(f"❌ MERGED_DIR not found: {MERGED_DIR}")
    if not (OV_DIR / 'model_fp16.xml').is_file():
        raise SystemExit(f"❌ OV model_fp16.xml not found in {OV_DIR}")

    print("🔹 Loading tokenizer & config...")
    tok = AutoTokenizer.from_pretrained(
        str(MERGED_DIR),
        use_fast=True,
        local_files_only=True,
        trust_remote_code=True,
    )
    cfg = AutoConfig.from_pretrained(
        str(MERGED_DIR),
        local_files_only=True,
        trust_remote_code=True,
    )
    eos_id = cfg.eos_token_id or tok.eos_token_id

    print("🔹 Loading OpenVINO model (BF16 hint)...")
    core = Core()
    core.set_property("CPU", {"INFERENCE_PRECISION_HINT": "bf16"})
    compiled_model = core.compile_model(str(OV_DIR / "model_fp16.xml"), "CPU")
    output_port = compiled_model.output(0)

    def greedy_generate(prompt: str, max_new_tokens: int = 96) -> str:
        enc = tok(prompt, return_tensors="np")
        input_ids = enc["input_ids"]
        attention_mask = enc["attention_mask"]

        for _ in range(max_new_tokens):
            res = compiled_model({"input_ids": input_ids,
                                  "attention_mask": attention_mask})
            logits = res[output_port]
            next_id = int(logits[0, -1].argmax())

            input_ids = np.concatenate([input_ids, [[next_id]]], axis=1)
            attention_mask = np.concatenate([attention_mask, [[1]]], axis=1)

            if eos_id is not None and next_id == eos_id:
                break

        full_text = tok.decode(input_ids[0], skip_special_tokens=True)
        completion = full_text[len(prompt):].strip()
        return completion

    prompts = load_prompts(PROMPTS)
    print(f"🔹 Loaded {len(prompts)} prompts from {PROMPTS}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as out_f:
        for idx, prompt in enumerate(prompts):
            print(f"\n=== [OV-HTN] Prompt {idx} ===")
            print(prompt)
            completion = greedy_generate(prompt)
            print("--- Completion (truncated) ---")
            print(completion[:300])

            rec = {
                "id": idx,
                "prompt": prompt,
                "completion": completion,
                "model": "xeon_htn_qwen_ov_bf16",
            }
            out_f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"\n✅ Saved OV HTN outputs to: {OUT}")

if __name__ == "__main__":
    main()
