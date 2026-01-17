#!/usr/bin/env python3
"""
rag_lipids_service.py

Lipids RAG Vector Service
- Stores docs in SQLite
- Builds FAISS index over embeddings (cosine sim via L2 normalize)
- Exposes:
    GET  /healthz
    POST /v1/lipids/index
    POST /v1/lipids/search
"""

import os
import sqlite3
from typing import List, Optional

import faiss
import numpy as np
from fastapi import FastAPI
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

# -------------------------------------------------------------------
# Paths / config
# -------------------------------------------------------------------
DB_PATH = os.getenv("RAG_DB_PATH", "lipids_docs.db")
EMB_MODEL_NAME = os.getenv("RAG_EMB_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
TOP_K_DEFAULT = int(os.getenv("RAG_TOP_K", "5"))

# If you want to allow more sources, add them here
ALLOWED_SOURCES = set(
    s.strip().lower()
    for s in os.getenv("RAG_ALLOWED_SOURCES", "internal,internal guideline").split(",")
    if s.strip()
)

# -------------------------------------------------------------------
# Pydantic schemas
# -------------------------------------------------------------------
class RagDoc(BaseModel):
    id: int
    title: str
    text: str
    tags: List[str] = []
    source: Optional[str] = None


class IndexRequest(BaseModel):
    docs: List[RagDoc]


class SearchRequest(BaseModel):
    query: str
    top_k: int = TOP_K_DEFAULT


class SearchHit(BaseModel):
    id: int
    score: float
    title: str
    text: str
    tags: List[str]
    source: Optional[str]


class SearchResponse(BaseModel):
    hits: List[SearchHit]


# -------------------------------------------------------------------
# App + globals
# -------------------------------------------------------------------
app = FastAPI(
    title="Lipids RAG Vector Service",
    version="1.0",
    description="RAG retrieval for Lipids diet agent",
)

emb_model: SentenceTransformer
faiss_index: Optional[faiss.IndexFlatIP] = None
dim: int = 0


# -------------------------------------------------------------------
# Safety: filter prompt-injection / canary docs
# -------------------------------------------------------------------
def _is_suspicious_doc(doc) -> bool:
    """
    Return True if we should exclude this doc from retrieval results.
    Supports dict OR pydantic model OR any object with attributes.
    """
    def _val(k, default=""):
        if isinstance(doc, dict):
            return doc.get(k, default)
        return getattr(doc, k, default)

    title = str(_val("title", "") or "").lower()
    text = str(_val("text", "") or "").lower()
    source = str(_val("source", "") or "").lower()
    tags = _val("tags", []) or []
    tags_l = [str(t).lower() for t in tags]

    # Block obvious canaries / injection markers
    if "canary" in title or "canary" in text or "canary" in tags_l:
        return True

    # Optional: only allow trusted sources
    if source and ALLOWED_SOURCES and source not in ALLOWED_SOURCES:
        return True

    return False


# -------------------------------------------------------------------
# SQLite helpers
# -------------------------------------------------------------------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_tables():
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS lipids_docs (
            id      INTEGER PRIMARY KEY,
            title   TEXT,
            text    TEXT,
            tags    TEXT,
            source  TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def load_all_docs():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, title, text, tags, source FROM lipids_docs")
    rows = cur.fetchall()
    conn.close()

    docs = []
    for r in rows:
        tags = (r["tags"] or "").split(",") if r["tags"] else []
        docs.append(
            {
                "id": r["id"],
                "title": r["title"],
                "text": r["text"],
                "tags": tags,
                "source": r["source"],
            }
        )
    return docs


# -------------------------------------------------------------------
# FAISS index build
# -------------------------------------------------------------------
def rebuild_faiss_index():
    global faiss_index, dim

    docs = load_all_docs()
    if not docs:
        faiss_index = None
        app.state.docs_cache = []
        return

    texts = [d["text"] for d in docs]
    embeddings = emb_model.encode(texts, convert_to_numpy=True)
    embeddings = embeddings.astype("float32")

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)

    # Normalize for cosine similarity
    faiss.normalize_L2(embeddings)

    index.add(embeddings)
    faiss_index = index

    # Store mapping order in memory
    app.state.docs_cache = docs


# -------------------------------------------------------------------
# FastAPI lifecycle
# -------------------------------------------------------------------
@app.on_event("startup")
def on_startup():
    global emb_model
    print("🔹 [LIPIDS-RAG] Loading embedding model:", EMB_MODEL_NAME)
    emb_model = SentenceTransformer(EMB_MODEL_NAME)

    ensure_tables()
    print(f"🔹 [LIPIDS-RAG] Using SQLite DB at: {DB_PATH}")

    rebuild_faiss_index()
    print("🔹 [LIPIDS-RAG] FAISS index built with docs:",
          len(getattr(app.state, "docs_cache", [])))


# -------------------------------------------------------------------
# Routes
# -------------------------------------------------------------------
@app.get("/healthz")
def healthz():
    return {
        "status": "ok",
        "service": "rag-lipids",
        "db_path": DB_PATH,
        "model": EMB_MODEL_NAME,
        "num_docs": len(getattr(app.state, "docs_cache", []))
        if hasattr(app.state, "docs_cache")
        else 0,
        "allowed_sources": sorted(ALLOWED_SOURCES) if ALLOWED_SOURCES else [],
    }


@app.post("/v1/lipids/index")
def index_docs(req: IndexRequest):
    """
    Ingest / upsert docs into the lipids RAG store.
    Rebuilds FAISS index after update (OK for < few 1000 docs).
    """
    conn = get_db()
    cur = conn.cursor()
    for d in req.docs:
        tags_str = ",".join(d.tags) if d.tags else ""
        cur.execute(
            """
            INSERT INTO lipids_docs (id, title, text, tags, source)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title=excluded.title,
                text=excluded.text,
                tags=excluded.tags,
                source=excluded.source
            """,
            (d.id, d.title, d.text, tags_str, d.source),
        )
    conn.commit()
    conn.close()

    rebuild_faiss_index()
    return {"status": "ok", "num_docs": len(getattr(app.state, "docs_cache", []))}


@app.post("/v1/lipids/search", response_model=SearchResponse)
def search_docs(req: SearchRequest):
    """
    Vector search over lipids docs using FAISS (cosine similarity).
    """
    if faiss_index is None or not getattr(app.state, "docs_cache", None):
        return SearchResponse(hits=[])

    query_vec = emb_model.encode([req.query], convert_to_numpy=True).astype("float32")
    faiss.normalize_L2(query_vec)

    k = min(req.top_k, len(app.state.docs_cache))
    scores, idxs = faiss_index.search(query_vec, k)  # (1, k)

    hits: List[SearchHit] = []
    for i in range(k):
        doc = app.state.docs_cache[int(idxs[0, i])]
        if _is_suspicious_doc(doc):
            continue
        hits.append(
            SearchHit(
                id=doc["id"],
                score=float(scores[0, i]),
                title=doc["title"],
                text=doc["text"],
                tags=doc["tags"],
                source=doc["source"],
            )
        )

    return SearchResponse(hits=hits)
