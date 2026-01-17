#!/usr/bin/env python3
"""
app/tools/diabetes_kg.py

Corrected Neo4j-based KG helper for diabetes.
Implements 'Hybrid Search':
1. Keyword lookup (if user mentions specific foods)
2. General Rules lookup (fallback for meal plans)
"""

import os
import logging
from typing import Any, Dict, List, Optional

from neo4j import GraphDatabase, Driver

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# Config
# -------------------------------------------------------------------
NEO4J_URI = os.getenv("DIAB_NEO4J_URI") or "bolt://192.168.2.69:7687"
NEO4J_USER = os.getenv("DIAB_NEO4J_USER") or "neo4j"
NEO4J_PASSWORD = os.getenv("DIAB_NEO4J_PASSWORD") or "neo4j123"

_driver: Optional[Driver] = None

def _get_driver() -> Optional[Driver]:
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
# STRATEGY 1: Look for specific foods mentioned in the query
# "Can I eat Rice?" -> Finds "White Rice", "Brown Rice"
# -------------------------------------------------------------------
CYPHER_FOOD_LOOKUP = """
MATCH (f:Food)
WHERE toLower($q) CONTAINS toLower(f.name)
MATCH (f)-[r]->(c:Condition)
WHERE toLower(c.name) CONTAINS 'diabetes'
RETURN 
  f.name AS name, 
  type(r) AS relationship, 
  coalesce(f.notes, '') AS notes
"""

# -------------------------------------------------------------------
# STRATEGY 2: Get General Rules for the Condition
# (Fallback if no specific food is mentioned)
# -------------------------------------------------------------------
CYPHER_GENERAL_RULES = """
MATCH (c:Condition)
WHERE toLower(c.name) CONTAINS 'diabetes'
MATCH (f:Food)-[r]->(c)
RETURN 
  f.name AS name, 
  type(r) AS relationship, 
  coalesce(f.notes, '') AS notes
ORDER BY f.name ASC
LIMIT 15
"""

def query_diabetes_kg(question: str, limit: int = 5) -> List[str]:
    """
    Query KG for facts. Returns a list of formatted strings like "Sugar: AVOID_FOR".
    """
    driver = _get_driver()
    if driver is None:
        return []

    q = (question or "").strip().lower()
    hits: List[str] = []

    try:
        with driver.session() as session:
            # 1. Try to find specific foods mentioned in the user's question
            food_records = session.run(CYPHER_FOOD_LOOKUP, {"q": q}).data()
            
            if food_records:
                for r in food_records:
                    rel = r['relationship'].replace('_FOR', '')
                    # Format: "White Rice: AVOID"
                    hits.append(f"{r['name']}: {rel}")
            
            # 2. If we didn't find specific foods (or user asked for a 'plan'), fetch general rules
            # We assume a "meal plan" query needs general guidance.
            if len(hits) < 3:
                rule_records = session.run(CYPHER_GENERAL_RULES).data()
                for r in rule_records:
                    rel = r['relationship'].replace('_FOR', '')
                    hits.append(f"{r['name']}: {rel}")

        # Remove duplicates just in case
        unique_hits = list(set(hits))
        
        logger.info("DIAB-KG: query='%s' -> found %d facts", question, len(unique_hits))
        return unique_hits[:limit]

    except Exception as e:
        logger.error("DIAB-KG: Error while querying KG: %s", e)
        return []