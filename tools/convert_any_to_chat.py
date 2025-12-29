#!/usr/bin/env python3
import sys, json, argparse

def to_chat(obj):
    # Already chat?
    if isinstance(obj.get("messages"), list):
        return {"messages": obj["messages"]}
    # Common patterns
    if "instruction" in obj and "output" in obj:
        # Alpaca-style (instruction, input?, output)
        instr = obj.get("instruction","").strip()
        inp   = obj.get("input","").strip()
        user  = (instr + ("\n" + inp if inp else "")).strip()
        return {"messages":[
            {"role":"system","content":"You are a helpful assistant."},
            {"role":"user","content":user},
            {"role":"assistant","content":obj["output"].strip()}
        ]}
    if "prompt" in obj and "completion" in obj:
        return {"messages":[
            {"role":"system","content":"You are a helpful assistant."},
            {"role":"user","content":obj["prompt"].strip()},
            {"role":"assistant","content":obj["completion"].strip()}
        ]}
    if "question" in obj and "answer" in obj:
        return {"messages":[
            {"role":"system","content":"You are a helpful assistant."},
            {"role":"user","content":obj["question"].strip()},
            {"role":"assistant","content":obj["answer"].strip()}
        ]}
    if "user" in obj and "assistant" in obj and isinstance(obj["user"], str) and isinstance(obj["assistant"], str):
        return {"messages":[
            {"role":"system","content":"You are a helpful assistant."},
            {"role":"user","content":obj["user"].strip()},
            {"role":"assistant","content":obj["assistant"].strip()}
        ]}
    # Last resort: single string under 'input' or 'text' -> treat as prompt-only (no target)
    if "text" in obj and isinstance(obj["text"], str):
        return {"messages":[
            {"role":"system","content":"You are a helpful assistant."},
            {"role":"user","content":obj["text"].strip()}
        ]}
    if "input" in obj and isinstance(obj["input"], str):
        return {"messages":[
            {"role":"system","content":"You are a helpful assistant."},
            {"role":"user","content":obj["input"].strip()}
        ]}
    raise ValueError(f"Unrecognized schema keys: {list(obj.keys())}")

def convert(inp, outp):
    n=0
    with open(inp, "r", encoding="utf-8") as fin, open(outp, "w", encoding="utf-8") as fout:
        for line in fin:
            line=line.strip()
            if not line: continue
            obj=json.loads(line)
            chat=to_chat(obj)
            fout.write(json.dumps(chat, ensure_ascii=False))
            fout.write("\n")
            n+=1
    print(f"✅ converted {n} lines -> {outp}")

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", dest="out", required=True)
    args=ap.parse_args()
    convert(args.inp, args.out)

