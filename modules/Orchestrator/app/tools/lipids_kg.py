#!/usr/bin/env python3
"""
app/tools/lipids_kg.py

Neo4j-based KG helper for Lipids (Cholesterol/Triglycerides).
Implements 'Hybrid Search':
1. Keyword lookup (if user mentions specific foods)
2. General Rules lookup (fallback for meal plans)
"""

import os
import logging
from typing import List, Optional
from neo4j import GraphDatabase, Driver

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# Config
# -------------------------------------------------------------------
NEO4J_URI = os.getenv("LIPIDS_NEO4J_URI") or "bolt://192.168.2.69:7687"
NEO4J_USER = os.getenv("LIPIDS_NEO4J_USER") or "neo4j"
NEO4J_PASSWORD = os.getenv("LIPIDS_NEO4J_PASSWORD") or "neo4j123"

_driver: Optional[Driver] = None

def _get_driver() -> Optional[Driver]:
    global _driver
    if _driver is not None:
        return _driver
    try:
        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        logger.info("LIPIDS-KG: created Neo4j driver for %s", NEO4J_URI)
    except Exception as e:
        logger.error("LIPIDS-KG: failed to create Neo4j driver: %s", e)
        _driver = None
    return _driver

# -------------------------------------------------------------------
# STRATEGY 1: Look for specific foods
# -------------------------------------------------------------------
CYPHER_FOOD_LOOKUP = """
MATCH (f:Food)
WHERE toLower($q) CONTAINS toLower(f.name)
MATCH (f)-[r]->(c:Condition)
WHERE toLower(c.name) CONTAINS 'hyperlipidemia' 
   OR toLower(c.name) CONTAINS 'cholesterol'
RETURN 
  f.name AS name, 
  type(r) AS relationship, 
  coalesce(f.notes, '') AS notes
"""

# -------------------------------------------------------------------
# STRATEGY 2: General Rules (Fallback)
# -------------------------------------------------------------------
CYPHER_GENERAL_RULES = """
MATCH (c:Condition)
WHERE toLower(c.name) CONTAINS 'hyperlipidemia'
MATCH (f:Food)-[r]->(c)
RETURN 
  f.name AS name, 
  type(r) AS relationship, 
  coalesce(f.notes, '') AS notes
ORDER BY f.name ASC
LIMIT 15
"""

def query_lipids_kg(question: str, limit: int = 5) -> List[str]:
    driver = _get_driver()
    if driver is None:
        return []

    q = (question or "").strip().lower()
    hits: List[str] = []

    try:
        with driver.session() as session:
            # 1. Try to find specific foods
            food_records = session.run(CYPHER_FOOD_LOOKUP, {"q": q}).data()
            if food_records:
                for r in food_records:
                    rel = r['relationship'].replace('_FOR', '')
                    hits.append(f"{r['name']}: {rel}")
            
            # 2. Fallback to general rules
            if len(hits) < 3:
                rule_records = session.run(CYPHER_GENERAL_RULES).data()
                for r in rule_records:
                    rel = r['relationship'].replace('_FOR', '')
                    hits.append(f"{r['name']}: {rel}")

        unique_hits = list(set(hits))
        logger.info("LIPIDS-KG: query='%s' -> found %d facts", question, len(unique_hits))
        return unique_hits[:limit]

    except Exception as e:
        logger.error("LIPIDS-KG: Error while querying KG: %s", e)
        return []