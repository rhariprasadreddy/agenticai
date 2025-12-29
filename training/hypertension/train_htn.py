#!/usr/bin/env python3
from datasets import load_dataset
from transformers import (
    AutoTokenizer, AutoModelForCausalLM, TrainingArguments,
    Trainer, DataCollatorForLanguageModeling
)
import torch

train_file = "train.jsonl"
val_file = "val.jsonl"

MODEL = "Qwen/Qwen2-1.5B-Instruct"  # or 7B

tokenizer = AutoTokenizer.from_pretrained(MODEL, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    MODEL,
    torch_dtype=torch.bfloat16,
    attn_implementation="flash_attention_2"
)

def tokenize(batch):
    return tokenizer(
        batch["text"], padding=False, truncation=True, max_length=2048
    )

# Convert JSONL → “text” dataset
ds = load_dataset("json", data_files={"train": train_file, "val": val_file})

def convert_messages(example):
    msgs = example["messages"]
    out = ""
    for m in msgs:
        out += f"{m['role']}: {m['content']}\n"
    return {"text": out}

ds = ds.map(convert_messages)

# Tokenize
tokenized = ds.map(tokenize, batched=True)

collator = DataCollatorForLanguageModeling(tokenizer, mlm=False)

args = TrainingArguments(
    output_dir="./outputs_htn",
    per_device_train_batch_size=4,
    per_device_eval_batch_size=4,
    gradient_accumulation_steps=4,
    num_train_epochs=3,
    bf16=True,
    logging_steps=50,
    evaluation_strategy="epoch",
    save_strategy="epoch",
    save_total_limit=2,
    report_to="none"
)

trainer = Trainer(
    model=model,
    args=args,
    data_collator=collator,
    train_dataset=tokenized["train"],
    eval_dataset=tokenized["val"]
)

trainer.train()
trainer.save_model("./final_htn")
tokenizer.save_pretrained("./final_htn")

