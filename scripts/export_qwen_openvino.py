#!/usr/bin/env python3
import argparse
from pathlib import Path

from optimum.intel.openvino import OVModelForCausalLM
from transformers import AutoTokenizer

ROOT = Path(__file__).resolve().parents[1]  # /home/agenticai/agenticai

def export_domain(domain: str):
    domain = domain.lower()
    assert domain in {"diabetes", "hypertension", "lipids"}, f"Unknown domain: {domain}"

    merged_dir = (ROOT / "models" / f"{domain}_qwen_merged_fp16").resolve()
    ov_fp16_dir = (ROOT / "models" / "openvino" / domain / "fp16").resolve()
    ov_bf16_dir = (ROOT / "models" / "openvino" / domain / "bf16").resolve()

    ov_fp16_dir.mkdir(parents=True, exist_ok=True)
    ov_bf16_dir.mkdir(parents=True, exist_ok=True)

    print(f"🔹 Domain        : {domain}")
    print(f"🔹 Merged HF dir : {merged_dir}")
    print(f"🔹 OV FP16 out   : {ov_fp16_dir}")
    print(f"🔹 OV BF16 out   : {ov_bf16_dir}")

    assert (merged_dir / "config.json").is_file(), f"❌ config.json missing in {merged_dir}"

    # shared tokenizer
    tok = AutoTokenizer.from_pretrained(merged_dir, use_fast=True)
    tok.save_pretrained(ov_fp16_dir)
    tok.save_pretrained(ov_bf16_dir)

    # ----- FP16 export -----
    print("🔹 Exporting FP16 OpenVINO IR...")
    ov_model_fp16 = OVModelForCausalLM.from_pretrained(
    merged_dir,
    export=True,
    compile=False,
    load_in_8bit=False,          # 🔴 explicitly disable 8-bit compression
    quantization_config=None,    # 🔴 no extra NNCF quantization
    ov_config={"INFERENCE_PRECISION_HINT": "f16"},
    )

    ov_model_fp16.save_pretrained(ov_fp16_dir)
    print("✅ Saved FP16 IR at:", ov_fp16_dir)

    # ----- BF16 export -----
    print("🔹 Exporting BF16 OpenVINO IR...")
    ov_model_bf16 = OVModelForCausalLM.from_pretrained(
    merged_dir,
    export=True,
    compile=False,
    load_in_8bit=False,
    quantization_config=None,
    ov_config={"INFERENCE_PRECISION_HINT": "bf16"},
    )
    ov_model_bf16.save_pretrained(ov_bf16_dir)
    print("✅ Saved BF16 IR at:", ov_bf16_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--domain",
        type=str,
        required=True,
        help="One of: diabetes, hypertension, lipids",
    )
    args = parser.parse_args()
    export_domain(args.domain)

