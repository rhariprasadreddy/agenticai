#!/usr/bin/env python3
import json
from pathlib import Path

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

# Paths INSIDE the GAUDI CONTAINER
MERGED = Path("/workspace/models/diabetes_qwen_merged_fp16")
PROMPTS = Path("/workspace/eval/prompts_diabetes.txt")
OUT = Path("/workspace/eval/gaudi_outputs.jsonl")

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
    print(f"🔹 Loading merged HF model from: {MERGED}")
    tok = AutoTokenizer.from_pretrained(
        str(MERGED),
        use_fast=True,
        trust_remote_code=True,
        local_files_only=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        str(MERGED),
        torch_dtype=torch.float16,
        trust_remote_code=True,
        local_files_only=True,
    )

    # Gaudi device
    try:
        import habana_frameworks.torch.hpu as hthpu  # noqa: F401
        device = torch.device("hpu")
    except Exception:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model.to(device)
    model.eval()

    eos_id = model.config.eos_token_id or tok.eos_token_id
    pad_id = tok.eos_token_id

    prompts = load_prompts(PROMPTS)
    print(f"🔹 Loaded {len(prompts)} prompts from {PROMPTS}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as out_f, torch.no_grad():
        for idx, prompt in enumerate(prompts):
            print(f"\n=== [Gaudi] Prompt {idx} ===")
            print(prompt)

            enc = tok(prompt, return_tensors="pt").to(device)
            input_ids = enc["input_ids"]

            gen_ids = model.generate(
                input_ids,
                max_new_tokens=96,
                do_sample=False,
                temperature=0.0,
                eos_token_id=eos_id,
                pad_token_id=pad_id,
            )

            full_text = tok.decode(gen_ids[0], skip_special_tokens=True)
            completion = full_text[len(prompt):].strip()

            print("--- Completion ---")
            print(completion[:300])

            rec = {
                "id": idx,
                "prompt": prompt,
                "completion": completion,
                "model": "gaudi_qwen_fp16",
            }
            out_f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"\n✅ Saved Gaudi outputs to: {OUT}")

if __name__ == "__main__":
    main()

