#!/usr/bin/env python3
import os
from neo4j import GraphDatabase

# Config
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://192.168.2.69:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASS", "neo4j123")

# DATA: Diabetes Knowledge Base
diabetes_data = [
    # ❌ AVOID (High GI, Sugar)
    ("White Rice", "AVOID_FOR", ["High GI"]),
    ("Maida (Refined Flour)", "AVOID_FOR", ["High GI"]),
    ("Sugar", "AVOID_FOR", ["Sucrose"]),
    ("Fruit Juice", "AVOID_FOR", ["Fructose Spike"]),
    ("Mango (Ripe)", "AVOID_FOR", ["High Sugar"]),
    ("Potato", "AVOID_FOR", ["High Starch"]),
    
    # ⚠️ LIMIT
    ("Brown Rice", "LIMIT_FOR", ["Carbohydrate"]),
    ("Chapati", "LIMIT_FOR", ["Carbohydrate"]),
    ("Banana", "LIMIT_FOR", ["Sugar"]),

    # ✅ RECOMMENDED (Low GI, Fiber)
    ("Oats", "RECOMMENDED_FOR", ["Beta-glucan"]),
    ("Methi (Fenugreek)", "RECOMMENDED_FOR", ["Soluble Fiber"]),
    ("Karela (Bitter Gourd)", "RECOMMENDED_FOR", ["Charantin"]),
    ("Jamun", "RECOMMENDED_FOR", ["Jamboline"]),
    ("Barley", "RECOMMENDED_FOR", ["Fiber"]),
    ("Moong Dal", "RECOMMENDED_FOR", ["Protein"]),
    ("Spinach", "RECOMMENDED_FOR", ["Magnesium"]),
    ("Almonds", "RECOMMENDED_FOR", ["Healthy Fats"]),
]

def seed_diabetes_data():
    print(f"🔌 Connecting to Neo4j at {NEO4J_URI}...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))

    with driver.session() as session:
        print("🏥 Creating 'Type 2 Diabetes' Condition Node...")
        session.run("MERGE (c:Condition {name: 'Type 2 Diabetes'})")

        for food_name, rel_type, nutrients in diabetes_data:
            print(f"   -> Processing: {food_name} ({rel_type})")
            query = f"""
            MERGE (f:Food {{name: $food_name}})
            MERGE (c:Condition {{name: 'Type 2 Diabetes'}})
            WITH f, c
            FOREACH (nut IN $nutrients | 
                MERGE (n:Nutrient {{name: nut}})
                MERGE (f)-[:HAS_NUTRIENT]->(n)
            )
            MERGE (f)-[:{rel_type}]->(c)
            """
            session.run(query, food_name=food_name, nutrients=nutrients)

    driver.close()
    print("✅ Diabetes KG Population Complete!")

if __name__ == "__main__":
    seed_diabetes_data()