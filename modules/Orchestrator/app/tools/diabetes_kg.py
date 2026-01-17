#!/usr/bin/env python3
"""
app/tools/diabetes_kg.py

Simple Neo4j-based KG helper for diabetes.
Runs inside the Orchestrator container and connects over Bolt
to the Neo4j server running on the Xeon inference node.
"""

import os
import logging
from typing import Any, Dict, List, Optional

from neo4j import GraphDatabase, Driver

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# Neo4j connection details (configured via environment variables)
# -------------------------------------------------------------------

NEO4J_URI = os.getenv("DIAB_NEO4J_URI") or "bolt://192.168.2.69:7687"
NEO4J_USER = os.getenv("DIAB_NEO4J_USER") or "neo4j"
NEO4J_PASSWORD = os.getenv("DIAB_NEO4J_PASSWORD") or "neo4j123"

_driver: Optional[Driver] = None


def _get_driver() -> Optional[Driver]:
    """
    Lazily create / return a shared Neo4j driver.
    """
    global _driver
    if _driver is not None:
        return _driver

    try:
        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        logger.info("DIAB-KG: created Neo4j driver for %s", NEO4J_URI)
    except Exception as e:
        logger.error("DIAB-KG: failed to create Neo4j driver: %s", e)
        _driver = None

    return _driver


# -------------------------------------------------------------------
# Cypher for your current schema: Condition / Food / Nutrient
# -------------------------------------------------------------------
# From Neo4j you showed:
#   Labels: Condition, Food, Nutrient
#   Properties: name, notes, tags
#
# We search across those three labels and three properties and
# then build a single 'text' field per hit so the rest of the
# pipeline can keep using 'text/topic/source/priority' if it wants.
# -------------------------------------------------------------------

CYPHER = """
WITH toLower($q) AS q
MATCH (n)
WHERE
  any(label IN labels(n) WHERE label IN ['Condition', 'Food', 'Nutrient'])
  AND (
    toLower(coalesce(n.name,  '')) CONTAINS q OR
    toLower(coalesce(n.notes, '')) CONTAINS q OR
    any(t IN coalesce(n.tags, []) WHERE toLower(t) CONTAINS q)
  )
RETURN
  labels(n)              AS labels,
  coalesce(n.name,  '')  AS name,
  coalesce(n.notes, '')  AS notes,
  coalesce(n.tags,  [])  AS tags
LIMIT $limit
"""


# -------------------------------------------------------------------
# Public API used by diabetes_qwen_ov.py
# -------------------------------------------------------------------
def query_diabetes_kg(question: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Query the diabetes KG for facts relevant to the free-text question.

    Returns a list of dicts with at least a 'text' field, and optionally
    'labels', 'name', 'notes', 'tags'. The 'text' field is a compact
    string summary used by the prompt builder.
    """
    driver = _get_driver()
    if driver is None:
        logger.warning("DIAB-KG: Neo4j driver unavailable; returning empty KG hits.")
        return []

    q = (question or "").strip()
    if not q:
        return []

    params = {"q": q.lower(), "limit": int(limit)}

    try:
        with driver.session() as session:
            records = session.run(CYPHER, params).data()

        hits: List[Dict[str, Any]] = []
        for r in records:
            labels = r.get("labels") or []
            name = (r.get("name") or "").strip()
            notes = (r.get("notes") or "").strip()
            tags = r.get("tags") or []

            # Build a compact text string from the available fields
            parts: List[str] = []
            if name:
                parts.append(name)
            if notes:
                parts.append(notes)
            if tags:
                parts.append("tags: " + ", ".join(tags))

            text = " — ".join(parts).strip()
            if not text:
                # nothing useful, skip
                continue

            hit = {
                "labels": labels,
                "name": name,
                "notes": notes,
                "tags": tags,
                # 'text' is what diabetes_qwen_ov._format_kg_evidence will use
                "text": text,
                # placeholders kept for compatibility
                "topic": "",
                "source": "",
                "priority": 0,
            }
            hits.append(hit)

        logger.info("DIAB-KG: KG hits count=%d for query=%r", len(hits), q)
        for h in hits:
            logger.info(
                "DIAB-KG: labels=%r name=%r notes_len=%d tags=%r",
                h.get("labels"),
                h.get("name"),
                len(h.get("notes") or ""),
                h.get("tags"),
            )

        return hits

    except Exception as e:
        logger.error("DIAB-KG: Error while querying KG: %s", e)
        return []


def format_kg_facts(hits: List[Dict[str, Any]], max_bullets: int = 5) -> str:
    """
    Turn KG hits into a compact bullet list that can be appended
    to the diabetes system prompt.

    Returns an empty string if there are no hits.
    """
    if not hits:
        return ""

    bullets: List[str] = []
    for h in hits[:max_bullets]:
        txt = (h.get("text") or "").strip()
        if not txt:
            continue
        labels = h.get("labels") or []
        label_str = f"[{', '.join(labels)}] " if labels else ""
        bullets.append(f"- {label_str}{txt}")

    if not bullets:
        return ""

    header = "Key structured facts from the diabetes knowledge graph:"
    return header + "\n" + "\n".join(bullets)


def close_driver():
    """
    Optional helper if you ever want to close the driver explicitly.
    """
    global _driver
    if _driver is not None:
        try:
            _driver.close()
            logger.info("DIAB-KG: Neo4j driver closed.")
        except Exception as e:
            logger.error("DIAB-KG: error closing driver: %s", e)
        finally:
            _driver = None

