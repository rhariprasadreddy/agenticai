#!/usr/bin/env python3
import os
from typing import List, Literal

from fastapi import FastAPI
from pydantic import BaseModel
from neo4j import GraphDatabase

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://192.168.2.69:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASS", "neo4j123")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))

app = FastAPI(
    title="Diabetes Diet KG Service",
    description="Neo4j-backed KG for Type 2 Diabetes diet constraints",
    version="1.0.0",
)


class FoodCheckRequest(BaseModel):
    condition: str = "Type 2 Diabetes"
    foods: List[str]


class FoodStatus(BaseModel):
    food: str
    status: Literal["RECOMMENDED", "OK", "LIMIT", "AVOID", "UNKNOWN"]
    reasons: List[str]


class FoodCheckResponse(BaseModel):
    condition: str
    results: List[FoodStatus]


@app.get("/health")
def health():
    return {"status": "ok", "neo4j_uri": NEO4J_URI}


def classify_food(tx, condition: str, food: str):
    """
    Look up the food in the KG and classify it for the condition.
    Priority: AVOID > LIMIT > RECOMMENDED > OK > UNKNOWN
    """
    query = """
    MATCH (f:Food {name: $food})
    OPTIONAL MATCH (f)-[r1:AVOID_FOR]->(c1:Condition {name: $cond})
    OPTIONAL MATCH (f)-[r2:LIMIT_FOR]->(c2:Condition {name: $cond})
    OPTIONAL MATCH (f)-[r3:RECOMMENDED_FOR]->(c3:Condition {name: $cond})
    OPTIONAL MATCH (f)-[r4:OK_FOR]->(c4:Condition {name: $cond})
    OPTIONAL MATCH (f)-[:HAS_NUTRIENT]->(n:Nutrient)
    RETURN f.name AS food,
           collect(DISTINCT type(r1)) AS avoid_rel,
           collect(DISTINCT type(r2)) AS limit_rel,
           collect(DISTINCT type(r3)) AS rec_rel,
           collect(DISTINCT type(r4)) AS ok_rel,
           collect(DISTINCT n.name)   AS nutrients
    """
    rec = tx.run(query, food=food, cond=condition).single()
    if rec is None:
        return {
            "food": food,
            "status": "UNKNOWN",
            "reasons": ["Food not found in KG"],
        }

    avoid_rel = [r for r in rec["avoid_rel"] if r]
    limit_rel = [r for r in rec["limit_rel"] if r]
    rec_rel   = [r for r in rec["rec_rel"] if r]
    ok_rel    = [r for r in rec["ok_rel"] if r]
    nutrients = [n for n in rec["nutrients"] if n]

    if avoid_rel:
        status = "AVOID"
        reasons = [f"Avoid for {condition}"] + [f"Nutrient: {n}" for n in nutrients]
    elif limit_rel:
        status = "LIMIT"
        reasons = [f"Limit for {condition}"] + [f"Nutrient: {n}" for n in nutrients]
    elif rec_rel:
        status = "RECOMMENDED"
        reasons = [f"Recommended for {condition}"] + [f"Nutrient: {n}" for n in nutrients]
    elif ok_rel:
        status = "OK"
        reasons = [f"Acceptable for {condition}"] + [f"Nutrient: {n}" for n in nutrients]
    else:
        status = "UNKNOWN"
        reasons = [f"No explicit relation for {condition}"] + [f"Nutrient: {n}" for n in nutrients]

    return {
        "food": food,
        "status": status,
        "reasons": reasons or ["No extra info"],
    }


@app.post("/v1/diabetes/kg/check_foods", response_model=FoodCheckResponse)
def check_foods(req: FoodCheckRequest):
    results = []
    with driver.session() as session:
        for f in req.foods:
            res = session.execute_read(classify_food, req.condition, f)
            results.append(FoodStatus(**res))
    return FoodCheckResponse(condition=req.condition, results=results)
