#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
from pathlib import Path
from typing import Dict, List, Any

# ---------------------- Args from environment ----------------------
# Keep the same Qwen2.5 base model (path or HF ID)
BASE_MODEL = os.getenv(
    "HTN_BASE_MODEL",
    "/workspace/.hf/models/qwen2.5-1.5b-instruct",
)

# Point to lipids JSONL we just created
TRAIN_FILE = os.getenv(
    "HTN_TRAIN_JSONL",
    "/workspace/data/kidney/curated/train.jsonl",
)
EVAL_FILE = os.getenv(
    "HTN_EVAL_JSONL",
    "/workspace/data/kidney/curated/val.jsonl",
)  # optional but recommended

OUT_DIR = os.getenv(
    "HTN_OUT_DIR",
    "/workspace/models/kidney_qwen_lora",
)

MAX_LEN = int(os.getenv("HTN_MAX_LEN", "2048"))
EPOCHS = float(os.getenv("HTN_EPOCHS", "2"))
BSZ = int(os.getenv("HTN_BSZ", "4"))
GACC = int(os.getenv("HTN_GACC", "8"))

# Local Gaudi config dir (must contain gaudi_config.json)
GAUDI_CFG_DIR = os.getenv("GAUDI_CFG_DIR", "/workspace/gaudi2_cfg")

# ---------------------- Basic assertions ---------------------------
assert Path(BASE_MODEL, "config.json").is_file(), \
    f"❌ Model path invalid: {BASE_MODEL}"
assert Path(TRAIN_FILE).is_file(), \
    f"❌ Kidney train jsonl missing: {TRAIN_FILE}"
if EVAL_FILE:
    assert Path(EVAL_FILE).is_file(), \
        f"❌ kidney eval jsonl missing: {EVAL_FILE}"
assert Path(GAUDI_CFG_DIR, "gaudi_config.json").is_file(), \
    f"❌ gaudi_config.json missing under {GAUDI_CFG_DIR}"

# ---------------------- Imports (Habana) ---------------------------
from datasets import load_dataset  # noqa: F401 (kept for parity with other scripts)
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    DataCollatorForLanguageModeling,
    GenerationConfig,
)
from peft import LoraConfig, get_peft_model

# ---------------- Gaudi imports ----------------
try:
    # new-style API (optimum-habana ≥1.10)
    from optimum.habana import GaudiTrainer, GaudiTrainingArguments
except ImportError:
    # fallback for older API
    from optimum.habana.habana_trainer import GaudiTrainer, GaudiTrainingArguments


# ---------------------- Dataset loader -----------------------------
def _jsonl_iter(path: str):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def detect_schema(sample: Dict[str, Any]) -> str:
    if "messages" in sample and isinstance(sample["messages"], list):
        return "chat"
    if "text" in sample and isinstance(sample["text"], str):
        return "text"
    # fallbacks: look for prompt/completion pair
    if "prompt" in sample and "completion" in sample:
        return "sft_pair"
    return "unknown"


def load_split(path: str):
    rows = list(_jsonl_iter(path))
    if not rows:
        raise RuntimeError(f"No rows in {path}")
    schema = detect_schema(rows[0])
    if schema == "unknown":
        raise RuntimeError(
            f"Unsupported schema in {path}; expected 'messages' or 'text' or prompt/completion"
        )
    return rows, schema


train_rows, schema = load_split(TRAIN_FILE)
eval_rows, schema_eval = ([], schema)
if EVAL_FILE and Path(EVAL_FILE).is_file():
    eval_rows, schema_eval = load_split(EVAL_FILE)


def make_hf_dataset(rows: List[Dict[str, Any]], schema_kind: str):
    from datasets import Dataset

    if schema_kind == "chat":
        return Dataset.from_list([{"messages": r["messages"]} for r in rows])
    if schema_kind == "text":
        return Dataset.from_list([{"text": r["text"]} for r in rows])
    if schema_kind == "sft_pair":
        return Dataset.from_list(
            [{"text": f"{r['prompt']}\n{r['completion']}"} for r in rows]
        )
    raise RuntimeError("Unsupported schema")


ds_train = make_hf_dataset(train_rows, schema)
ds_eval = make_hf_dataset(eval_rows, schema_eval) if eval_rows else None

# ---------------------- Tokenizer & chat template -------------------
tok = AutoTokenizer.from_pretrained(
    BASE_MODEL,
    use_fast=True,
    local_files_only=True,
)
if tok.pad_token is None:
    tok.pad_token = tok.eos_token
if tok.pad_token_id is None:
    tok.pad_token_id = tok.eos_token_id


def to_text(batch):
    """
    Robustly turn a HF batch (dict-of-lists) or a list of records into a list[str].
    Accepts:
      - {'messages': [list[chat_turns], ...]}
      - {'text': [str, ...]}
      - [ {'messages': [...]}, {'messages': [...]}, ... ]
      - [ 'some text', 'some text', ... ]
      - {'messages': ['[{"role":"user",...}]', ...]}  # stringified JSON
    """
    texts = []

    # Case A: dict-of-lists (batched=True normal path)
    if isinstance(batch, dict):
        if "messages" in batch:
            for msgs in batch["messages"]:
                if isinstance(msgs, str):
                    try:
                        msgs = json.loads(msgs)
                    except Exception:
                        raise ValueError("messages is a string but not valid JSON")
                s = tok.apply_chat_template(
                    msgs, tokenize=False, add_generation_prompt=False
                )
                texts.append(s)
        elif "text" in batch:
            for t in batch["text"]:
                texts.append(t if isinstance(t, str) else str(t))
        else:
            raise ValueError(f"Unsupported batch keys: {list(batch.keys())}")
        return texts

    # Case B: list
    if isinstance(batch, list):
        for item in batch:
            if isinstance(item, dict):
                if "messages" in item:
                    msgs = item["messages"]
                    if isinstance(msgs, str):
                        msgs = json.loads(msgs)
                    s = tok.apply_chat_template(
                        msgs, tokenize=False, add_generation_prompt=False
                    )
                    texts.append(s)
                elif "text" in item:
                    texts.append(
                        item["text"]
                        if isinstance(item["text"], str)
                        else str(item["text"])
                    )
                else:
                    raise ValueError(f"Unsupported item keys: {list(item.keys())}")
            elif isinstance(item, str):
                texts.append(item)
            else:
                texts.append(str(item))
        return texts

    # Fallback
    return [str(batch)]


def tokenize_fn(examples):
    texts = to_text(examples)
    enc = tok(texts, padding=False, truncation=True, max_length=MAX_LEN)
    enc["labels"] = enc["input_ids"].copy()
    return enc


column_names = ds_train.column_names
ds_tr = ds_train.map(tokenize_fn, batched=True, remove_columns=column_names)
ds_ev = None
if ds_eval:
    ds_ev = ds_eval.map(
        tokenize_fn, batched=True, remove_columns=ds_eval.column_names
    )

collator = DataCollatorForLanguageModeling(tok, mlm=False)

# ---------------------- Model & GenConfig patch ---------------------
model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    local_files_only=True,
)
model.config.use_cache = False  # required when using gradient_checkpointing


def normalize_genconfig(m):
    gc = getattr(m, "generation_config", None) or GenerationConfig()

    required_false = [
        "attn_softmax_bf16",
        "use_flash_attention",
        "use_flash_attention_2",
        "flash_attention_recompute",
        "flash_attention_causal_mask",
        "hpu_graphs",
        "flash_attention_dropout",
        "flash_attention_window",
        "flash_attention_scale",
        "flash_attention_fuse_softmax",
        "flash_attention_fuse_qk",
        "flash_attention_fp8",
        "flash_attention_quantization",
        "flash_attention_query_key_layer_scaling",
    ]

    for k in required_false:
        if not hasattr(gc, k):
            setattr(gc, k, False)

    m.generation_config = gc
    print(
        "✅ GenConfig normalized:",
        {k: getattr(m.generation_config, k, None) for k in required_false},
    )


normalize_genconfig(model)

# ---------------------- LoRA (lightweight) --------------------------
peft_cfg = LoraConfig(
    r=16,
    lora_alpha=16,
    lora_dropout=0.1,
    target_modules=[
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
    ],
    task_type="CAUSAL_LM",
)
model = get_peft_model(model, peft_cfg)

model.config.use_cache = False
if hasattr(model, "enable_input_require_grads"):
    model.enable_input_require_grads()
if hasattr(model, "gradient_checkpointing_enable"):
    model.gradient_checkpointing_enable()

# ---------------------- Gaudi training args -------------------------
args = GaudiTrainingArguments(
    output_dir=OUT_DIR,
    per_device_train_batch_size=BSZ,
    per_device_eval_batch_size=max(1, BSZ),
    gradient_accumulation_steps=GACC,
    learning_rate=2e-4,
    num_train_epochs=EPOCHS,
    logging_steps=10,
    evaluation_strategy="steps" if ds_ev is not None else "no",
    eval_steps=100,
    save_strategy="epoch",
    bf16=True,
    lr_scheduler_type="cosine",
    warmup_ratio=0.03,
    gradient_checkpointing=True,
    gradient_checkpointing_kwargs={"use_reentrant": False},
    do_eval=bool(ds_ev is not None),
    dataloader_num_workers=2,
    seed=42,
    use_habana=True,
    use_lazy_mode=False,
    use_hpu_graphs_for_training=False,
    use_hpu_graphs_for_inference=False,
    gaudi_config_name=GAUDI_CFG_DIR,
)

if not getattr(args, "gaudi_config_name", None):
    args.gaudi_config_name = GAUDI_CFG_DIR
assert Path(args.gaudi_config_name, "gaudi_config.json").exists(), \
    "gaudi_config.json not found where expected"

print(f"✅ Using local Gaudi config dir: {args.gaudi_config_name}")

trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
total = sum(p.numel() for p in model.parameters())
print(f"✅ trainable params: {trainable:,} / {total:,}")

# ---------------------- Trainer ------------------------------
trainer = GaudiTrainer(
    model=model,
    args=args,
    tokenizer=tok,
    data_collator=collator,
    train_dataset=ds_tr,
    eval_dataset=ds_ev,
)

# ---------------------- Train & save -------------------------
train_result = trainer.train()
trainer.save_model(OUT_DIR)
tok.save_pretrained(OUT_DIR)

print("✅ kidney training done. Adapters saved to:", OUT_DIR)

