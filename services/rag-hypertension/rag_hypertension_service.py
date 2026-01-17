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
DB_PATH = os.getenv("RAG_DB_PATH", "hypertension_docs.db")
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
    title="Hypertension RAG Vector Service",
    description="FAISS-based RAG service for HTN diet guidelines",
    version="0.1.0",
)


# -------------------------------------------------------------------
# Safety: filter prompt-injection / canary docs
# -------------------------------------------------------------------

def _is_suspicious_doc(doc: dict) -> bool:
    title = str(doc.get("title", "")).lower()
    text = str(doc.get("text", "")).lower()
    source = str(doc.get("source", "") or "").lower()
    tags = doc.get("tags", []) or []
    tags_l = [str(t).lower() for t in tags]

    if "canary" in title or "canary" in text:
        return True
    if "canary" in tags_l:
        return True
    # Optional: only allow trusted sources
    if source and source not in ("internal guideline", "internal", "healthhub/icmr"):
        return True
    return False


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
        CREATE TABLE IF NOT EXISTS hypertension_docs (
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
    cur.execute("SELECT id, title, text, tags, source FROM hypertension_docs")
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
    embeddings = emb_model.encode(texts, convert_to_numpy=True)
    embeddings = embeddings.astype("float32")

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)

    # Optional: normalize for cosine similarity
    faiss.normalize_L2(embeddings)

    index.add(embeddings)
    faiss_index = index

    # Store mapping order in memory
    app.state.docs_cache = docs


@app.on_event("startup")
def on_startup():
    global emb_model
    print("🔹 Loading embedding model:", EMB_MODEL_NAME)
    emb_model = SentenceTransformer(EMB_MODEL_NAME)

    ensure_tables()
    print(f"🔹 Using SQLite DB at: {DB_PATH}")
    rebuild_faiss_index()
    print("🔹 FAISS index built with docs:",
          len(getattr(app.state, "docs_cache", [])))


@app.get("/healthz")
def healthz():
    return {
        "status": "ok",
        "db_path": DB_PATH,
        "model": EMB_MODEL_NAME,
        "num_docs": len(getattr(app.state, "docs_cache", []))
        if hasattr(app.state, "docs_cache")
        else 0,
    }


@app.post("/v1/hypertension/index")
def index_docs(req: IndexRequest):
    """
    Ingest or upsert docs into the Hypertension RAG store.
    For now we simply overwrite rows with same id and rebuild the FAISS index.
    """
    conn = get_db()
    cur = conn.cursor()
    for d in req.docs:
        tags_str = ",".join(d.tags) if d.tags else ""
        cur.execute(
            """
            INSERT INTO hypertension_docs (id, title, text, tags, source)
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

    # Rebuild entire FAISS index (OK for < few 1000 docs)
    rebuild_faiss_index()
    return {"status": "ok", "num_docs": len(app.state.docs_cache)}

def _is_suspicious_doc(doc) -> bool:
    # Accept dict OR pydantic model OR any object with attributes
    def _val(k, default=""):
        if isinstance(doc, dict):
            return doc.get(k, default)
        return getattr(doc, k, default)

    title = str(_val("title", "") or "").lower()
    text = str(_val("text", "") or "").lower()
    source = str(_val("source", "") or "").lower()
    tags = _val("tags", []) or []
    tags_l = [str(t).lower() for t in tags]

    if "canary" in title or "canary" in text:
        return True
    if "canary" in tags_l:
        return True
    if source and source not in ("internal guideline", "internal", "healthhub/icmr"):
        return True
    return False

@app.post("/v1/hypertension/search", response_model=SearchResponse)
def search_docs(req: SearchRequest):
    """
    Vector search over hypertension docs using FAISS.
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
