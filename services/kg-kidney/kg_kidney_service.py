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

app = FastAPI(title="Kidney Diet KG Service", version="1.0.0")

class FoodCheckRequest(BaseModel):
    condition: str = "ckd"
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
    if rec is None: return {"food": food, "status": "UNKNOWN", "reasons": ["Not in KG"]}
    
    # Logic: Avoid > Limit > Recommended > OK
    if rec["avoid_rel"]: status, prefix = "AVOID", "Avoid"
    elif rec["limit_rel"]: status, prefix = "LIMIT", "Limit"
    elif rec["rec_rel"]: status, prefix = "RECOMMENDED", "Recommended"
    elif rec["ok_rel"]: status, prefix = "OK", "OK"
    else: status, prefix = "UNKNOWN", "No relation"
    
    reasons = [f"{prefix} for {condition}"] + [f"Nutrient: {n}" for n in rec["nutrients"]]
    return {"food": food, "status": status, "reasons": reasons}

@app.post("/v1/kidney/kg/check_foods", response_model=FoodCheckResponse)
def check_foods(req: FoodCheckRequest):
    results = []
    with driver.session() as session:
        for f in req.foods:
            res = session.execute_read(classify_food, req.condition, f)
            results.append(FoodStatus(**res))
    return FoodCheckResponse(condition=req.condition, results=results)