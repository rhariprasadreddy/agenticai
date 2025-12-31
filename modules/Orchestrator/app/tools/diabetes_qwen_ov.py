#!/usr/bin/env python3
"""
app/tools/diabetes_qwen_ov.py

Diabetes specialist agent for T2DM, now integrating:
- System prompt (rules + format)
- RAG evidence from FAISS service
- KG evidence from Neo4j diabetes KG

Used by the MCP Orchestrator's router.
"""

import os
import requests

# Diabetes OV server running on inference host (Xeon)
DIABETES_OV_URL = os.getenv(
    "DIABETES_OV_URL",
import re
import logging
from typing import Optional, List, Dict, Any

import requests

from .diabetes_kg import query_diabetes_kg  # Neo4j helper

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# Endpoints (Xeon inference + RAG)
# ----------------------------------------------------------------------

# Default: Xeon OV diabetes generation service
DIABETES_QWEN_OV_URL = os.getenv(
    "DIABETES_QWEN_OV_URL",
    "http://192.168.2.69:8080",
)

# RAG service on Xeon (FAISS + FastAPI)
DIABETES_RAG_URL = os.getenv(
    "DIABETES_RAG_URL",
    "http://192.168.2.69:9101",
)

MAX_NEW_TOKENS = int(os.getenv("DIABETES_MAX_NEW_TOKENS", "280"))

# ----------------------------------------------------------------------
# Structured system prompt – Diabetes, Indian vegetarian, Lipids-style layout
# ----------------------------------------------------------------------
SYSTEM_PROMPT = """
You are a clinical diet specialist focused on Type 2 Diabetes management in Indian adults.

STRICT RULES:
- Use ONLY Indian vegetarian foods (idli, dosa, upma, poha, roti, sabzi, dal, curd, millets, khichdi, etc.).
- Do NOT recommend:
  - Alcohol in any form
  - Fruit juices, sweets, jaggery, honey, sugarcane juice, soft drinks
  - Refined flour items (maida), deep-fried snacks, bakery sweets
- Focus on:
  - Low–GI carbohydrates
  - High fibre (vegetables, whole grains, dals)
  - Adequate protein (dal, paneer, curd, soy, pulses)
  - Healthy fats (groundnut, sesame, mustard, rice bran oil in small amounts)
- Portions must be realistic for an adult Indian patient.
- Response must be UNDER 300 words.
- Do NOT repeat the “Patient request” text.
- Do NOT add extra sections or extra conversations.
- ONLY output the sections below, in this exact order.

OUTPUT FORMAT (exact headings, bullet points):
# Strict, structured system prompt for Type 2 Diabetes (T2DM)
# ----------------------------------------------------------------------
SYSTEM_PROMPT = """
You are a clinical dietitian specialized in Type 2 Diabetes (T2DM) in Indian adults.

GOALS:
- Smooth blood sugar control (avoid sharp post-meal spikes).
- Support weight management and long-term HbA1c reduction.

ABSOLUTE RULES:
- Do NOT recommend: sugar, sweets, desserts, laddoo, halwa, jaggery, honey, candy,
  cakes, pastries, sweet drinks, fruit juice, sugarcane juice, soft drinks.
- Do NOT recommend: fried snacks (samosa, pakoda, bhujia, chips), papad, bakery biscuits,
  namkeen mixtures, deep-fried street foods.
- Use ONLY common Indian vegetarian foods (idli, dosa, upma, poha, roti, sabzi, dal, curd,
  salads, sprouts, millets, buttermilk, etc.).
- Prefer: low-GI carbs, high fibre, adequate protein, small amounts of healthy fats
  (nuts, seeds, groundnut / gingelly / rice bran oil).
- Mention portions in everyday terms (e.g. 2 idlis, 1 small katori, 1 medium phulka).
- KEEP THE RESPONSE UNDER 280 WORDS.
- Do NOT repeat these instructions or the patient question.
- Do NOT use placeholders like [avoid] or similar markers. Simply omit restricted foods.
- Do NOT start a conversation or ask follow-up questions. Answer once and stop.

EVIDENCE USE:
- You may receive evidence from:
  - RAG: unstructured internal guidelines.
  - KG: structured diabetes facts and relationships.
- When evidence is present, align your advice with it and do NOT contradict it.
- If evidence is sparse or missing, answer using your core diabetes knowledge and rules.

OUTPUT FORMAT (use EXACTLY these headings and structure):

Breakfast:
- Option 1: ...
- Option 2: ...

Mid-morning snack:
- Option 1: ...
- Option 2: ...

Lunch:
- Option 1: ...
- Option 2: ...

Evening snack:
- Option 1: ...
- Option 2: ...

Dinner:
- Option 1: ...
- Option 2: ...

General Guidelines:
- 4–6 bullet points for lifestyle, carb control, and HbA1c reduction.

STOP after the General Guidelines bullets. Do NOT write anything else.
- Bullet 1 ...
- Bullet 2 ...
- Bullet 3 ...
- Bullet 4 ...
- Bullet 5 ...

Make each option 1–2 practical Indian vegetarian items.
Tone must be clear, practical and reassuring. Do not use ALL CAPS headings.
""".strip()

# ----------------------------------------------------------------------
# Simple diabetes-intent detector (router helper)
# ----------------------------------------------------------------------

def build_diabetes_prompt(user_message: str) -> str:
    return (
        SYSTEM_PROMPT
        + "\n\nPatient request:\n"
        + user_message.strip()
        + "\n\nNow generate the 1-day diabetes meal plan in the exact required format:\n"
    )


def is_diabetes_query(text: str) -> bool:
    t = text.lower()
    keywords = [
        "diabetes",
        "diabetic",
        "blood sugar",
        "glucose",
        "hba1c",
        "t2dm",
        "type 2",
        "type-2",
        "insulin",
        "metformin",
    ]
    return any(k in t for k in keywords)


def call_diabetes_qwen(user_message: str, max_new_tokens: int = 220) -> str:
    """
    Call the Xeon OpenVINO diabetes Qwen service with a strict, structured prompt.
_DIABETES_PAT = re.compile(
    r"\b(diabetes|diabetic|blood sugar|sugar levels?|glucose|"
    r"hba1c|fasting sugar|fbs|ppbs|t2dm|type 2 diabetes)\b",
    flags=re.IGNORECASE,
)


def is_diabetes_query(text: Optional[str]) -> bool:
    if not text:
        return False
    return bool(_DIABETES_PAT.search(text))


# ----------------------------------------------------------------------
# RAG helper – FAISS diabetes search
# ----------------------------------------------------------------------

def _query_diabetes_rag(question: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Call the diabetes RAG service on Xeon (FAISS backend).
    FastAPI schema:
      POST /v1/diabetes/search
      { "query": str, "top_k": int }
    Response:
      { "hits": [ { "id": int, "title": str, "text": str, "score": float, ... }, ... ] }
    """
    url = f"{DIABETES_RAG_URL}/v1/diabetes/search"
    payload = {"query": question, "top_k": top_k}

    try:
        resp = requests.post(url, json=payload, timeout=5.0)
        resp.raise_for_status()
        data = resp.json() or {}
        hits = data.get("hits", []) or []

        # Debug logs (visible in docker logs)
        print(f"[DIAB-RAG] query={question!r} top_k={top_k} hits={len(hits)}", flush=True)
        for h in hits:
            print(
                f"[DIAB-RAG] id={h.get('id')} title={h.get('title')} score={h.get('score')}",
                flush=True,
            )

        logger.info("[DIAB-RAG] RAG hits count=%d", len(hits))
        return hits
    except Exception as e:
        logger.warning("[DIAB-RAG] error calling RAG: %s", e)
        print(f"[DIAB-RAG] ERROR: {e}", flush=True)
        return []


def _format_rag_evidence(hits: List[Dict[str, Any]]) -> str:
    if not hits:
        return "No RAG evidence retrieved."

    lines = ["Top retrieved diabetes diet evidence (RAG):"]
    for h in hits:
        title = (h.get("title") or "Untitled").strip()
        text = (h.get("text") or "").strip()
        score = h.get("score")
        if score is not None:
            lines.append(f"- [{score:.2f}] {title}: {text}")
        else:
            lines.append(f"- {title}: {text}")
    return "\n".join(lines)


# ----------------------------------------------------------------------
# KG helper – Neo4j diabetes KG
# ----------------------------------------------------------------------

def _query_diabetes_kg(question: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Wrapper around diabetes_kg.query_diabetes_kg with logging.
    """
    try:
        q_lower = (question or "").lower()
        if "diabetes" in q_lower or "t2dm" in q_lower:
            kg_query = "diabetes"
        else:
            kg_query = question or ""

        facts = query_diabetes_kg(kg_query, limit=top_k) or []

        print(
            f"[DIAB-KG] question={question!r} kg_query={kg_query!r} facts={len(facts)}",
            flush=True,
        )
        for f in facts:
            txt = f.get("text") or f.get("name") or repr(f)
            print(f"[DIAB-KG] fact={txt}", flush=True)

        logger.info(
            "[DIAB-KG] KG facts count=%d for question=%r (kg_query=%r)",
            len(facts),
            question,
            kg_query,
        )
        return facts
    except Exception as e:
        logger.warning("[DIAB-KG] error calling KG: %s", e)
        print(f"[DIAB-KG] ERROR: {e}", flush=True)
        return []


def _format_kg_evidence(facts: List[Dict[str, Any]]) -> str:
    """
    Format Neo4j KG facts into a readable bullet list for the prompt.
    """
    if not facts:
        return "No KG evidence retrieved."

    lines: List[str] = ["Top structured diabetes facts (KG):"]
    for f in facts:
        if isinstance(f, str):
            lines.append(f"- {f}")
        elif isinstance(f, dict):
            text = (
                f.get("text")
                or f.get("name")
                or f.get("notes")
                or f.get("description")
                or f.get("summary")
                or repr(f)
            )
            lines.append(f"- {text}")
        else:
            lines.append(f"- {repr(f)}")

    return "\n".join(lines)


# ----------------------------------------------------------------------
# Prompt builder – System + RAG + KG + user message
# ----------------------------------------------------------------------

def build_diabetes_prompt(
    user_message: str,
    use_rag: bool = True,
    use_kg: bool = True,
) -> str:
    """
    Build the full prompt given a free-text patient request.
    Optionally augments with:
      - RAG evidence from FAISS
      - KG evidence from Neo4j
    """
    user_message = (user_message or "").strip()

    context_parts: List[str] = []

    if use_rag:
        hits = _query_diabetes_rag(user_message, top_k=3)
        rag_block = _format_rag_evidence(hits)
        context_parts.append("## Evidence from RAG (internal guidelines)\n" + rag_block)

    if use_kg:
        facts = _query_diabetes_kg(user_message, top_k=5)
        kg_block = _format_kg_evidence(facts)
        context_parts.append("## Evidence from KG (structured diabetes knowledge)\n" + kg_block)

    if context_parts:
        context_section = "\n\n".join(context_parts)
    else:
        context_section = "## Evidence:\n- No external RAG or KG evidence was retrieved. Answer using core diabetes rules."

    full_prompt = (
        SYSTEM_PROMPT
        + "\n\n"
        + "Patient request:\n"
        + (user_message or "No additional notes provided.")
        + "\n\n"
        + "Evidence (RAG + KG):\n"
        + context_section
        + "\n\n"
        + "Task:\n"
        + "Generate the 1-day diabetes meal plan in the EXACT required format. "
          "Do NOT use markdown headings. Use only the headings exactly as defined."
    )

    return full_prompt.strip()


# ----------------------------------------------------------------------
# Call into Xeon OpenVINO Diabetes service
# ----------------------------------------------------------------------

def call_diabetes_qwen(
    user_message: str,
    timeout: float = 60.0,
    use_rag: bool = True,
    use_kg: bool = True,
) -> str:
    """
    Router-facing wrapper:
    - Builds prompt from system + RAG + KG + user message
    - Calls OV diabetes endpoint
    - Returns only the reply text
    """
    url = f"{DIABETES_QWEN_OV_URL}/generate"
    prompt = build_diabetes_prompt(user_message, use_rag=use_rag, use_kg=use_kg)

    payload = {
        "prompt": prompt,
        "max_new_tokens": MAX_NEW_TOKENS,
    }

    print(f"[DIAB-OV] Calling Diabetes OV at {url}", flush=True)
    logger.info("Calling Diabetes OV at %s", url)

    try:
        r = requests.post(url, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        return (data.get("completion") or data.get("text", "")).strip()
        resp = requests.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json() or {}

        text = data.get("reply") or data.get("completion") or data.get("text") or ""
        return text.strip()
    except Exception as e:
        logger.error("Diabetes Qwen OV error: %s", e)
        print(f"[DIAB-OV] ERROR: {e}", flush=True)
        return f"[Diabetes Qwen OV error: {e}]"

