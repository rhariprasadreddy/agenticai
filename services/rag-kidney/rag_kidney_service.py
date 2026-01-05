#!/usr/bin/env python3
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
DB_PATH = os.getenv("RAG_DB_PATH", "kidney_docs.db")
EMB_MODEL_NAME = os.getenv("RAG_EMB_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
TOP_K_DEFAULT = int(os.getenv("RAG_TOP_K", "5"))

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
    title="Kidney (CKD) RAG Vector Service",
    description="FAISS-based RAG service for CKD renal diet guidelines",
    version="0.1.0",
)

emb_model: SentenceTransformer
faiss_index: Optional[faiss.IndexFlatIP] = None
dim: int = 0


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_tables():
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS kidney_docs (
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
    cur.execute("SELECT id, title, text, tags, source FROM kidney_docs")
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


def rebuild_faiss_index():
    global faiss_index, dim

    docs = load_all_docs()
    if not docs:
        faiss_index = None
        return

    texts = [d["text"] for d in docs]
    embeddings = emb_model.encode(texts, convert_to_numpy=True).astype("float32")
    dim = embeddings.shape[1]

    index = faiss.IndexFlatIP(dim)
    faiss.normalize_L2(embeddings)
    index.add(embeddings)
    faiss_index = index

    app.state.docs_cache = docs


def _is_suspicious_doc(doc: dict) -> bool:
    """
    Keep it simple. Drop any doc containing canary / test / placeholder-like markers.
    Extend this later if needed.
    """
    text = ((doc.get("title") or "") + " " + (doc.get("text") or "")).lower()
    bad = ["canary", "lorem ipsum", "placeholder", "dummy"]
    return any(b in text for b in bad)


@app.on_event("startup")
def on_startup():
    global emb_model
    print("🔹 Loading embedding model:", EMB_MODEL_NAME)
    emb_model = SentenceTransformer(EMB_MODEL_NAME)

    ensure_tables()
    print(f"🔹 Using SQLite DB at: {DB_PATH}")
    rebuild_faiss_index()
    print("🔹 FAISS index built with docs:", len(getattr(app.state, "docs_cache", [])))


@app.get("/healthz")
def healthz():
    return {
        "status": "ok",
        "db_path": DB_PATH,
        "model": EMB_MODEL_NAME,
        "num_docs": len(getattr(app.state, "docs_cache", [])) if hasattr(app.state, "docs_cache") else 0,
    }


@app.post("/v1/kidney/index")
def index_docs(req: IndexRequest):
    conn = get_db()
    cur = conn.cursor()
    for d in req.docs:
        tags_str = ",".join(d.tags) if d.tags else ""
        cur.execute(
            """
            INSERT INTO kidney_docs (id, title, text, tags, source)
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
    return {"status": "ok", "num_docs": len(app.state.docs_cache)}


@app.post("/v1/kidney/search", response_model=SearchResponse)
def search_docs(req: SearchRequest):
    if faiss_index is None or not getattr(app.state, "docs_cache", None):
        return SearchResponse(hits=[])

    query_vec = emb_model.encode([req.query], convert_to_numpy=True).astype("float32")
    faiss.normalize_L2(query_vec)

    k = min(req.top_k, len(app.state.docs_cache))
    scores, idxs = faiss_index.search(query_vec, k)

    hits: List[SearchHit] = []
    kept = 0
    dropped = 0
    for i in range(k):
        doc = app.state.docs_cache[int(idxs[0, i])]
        if _is_suspicious_doc(doc):
            dropped += 1
            continue
        kept += 1
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

    print(
        f"[KIDNEY-RAG] query={req.query!r} top_k={req.top_k} hits_kept={kept} dropped_suspicious={dropped}",
        flush=True,
    )
    for h in hits[: min(kept, 5)]:
        print(f"[KIDNEY-RAG] id={h.id} title={h.title} score={h.score}", flush=True)

    return SearchResponse(hits=hits)

