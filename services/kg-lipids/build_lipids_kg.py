#!/usr/bin/env python3
import os
from neo4j import GraphDatabase

# Config
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://192.168.2.69:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASS", "neo4j123")

# DATA: Lipids Knowledge Base
# Focus: Saturated Fats, Trans Fats, Sugar (for TG), Fiber
lipids_data = [
    # ❌ AVOID (High Saturated/Trans Fats/Sugar)
    ("Vanaspati (Dalda)", "AVOID_FOR", ["Trans Fat"]),
    ("Red Meat (Mutton)", "AVOID_FOR", ["Saturated Fat", "Cholesterol"]),
    ("Full-fat Milk", "AVOID_FOR", ["Saturated Fat"]),
    ("Processed Cheese", "AVOID_FOR", ["Saturated Fat", "Sodium"]),
    ("Pastries/Cakes", "AVOID_FOR", ["Trans Fat", "Sugar"]),
    ("Deep Fried Foods", "AVOID_FOR", ["Trans Fat"]),
    ("Coconut Oil", "LIMIT_FOR", ["Saturated Fat"]),
    ("Ghee", "LIMIT_FOR", ["Saturated Fat"]),
    ("Egg Yolk", "LIMIT_FOR", ["Cholesterol"]),
    ("White Bread", "LIMIT_FOR", ["Refined Carbs"]), # Bad for Triglycerides

    # ✅ RECOMMENDED (Fiber, Omega-3, MUFA)
    ("Oats", "RECOMMENDED_FOR", ["Soluble Fiber"]), # Lowers LDL
    ("Walnuts", "RECOMMENDED_FOR", ["Omega-3"]),
    ("Flax Seeds", "RECOMMENDED_FOR", ["Omega-3"]),
    ("Almonds", "RECOMMENDED_FOR", ["MUFA"]),
    ("Salmon/Fatty Fish", "RECOMMENDED_FOR", ["Omega-3"]),
    ("Olive Oil", "RECOMMENDED_FOR", ["MUFA"]),
    ("Garlic", "RECOMMENDED_FOR", ["Allicin"]),
    ("Methi (Fenugreek) Seeds", "RECOMMENDED_FOR", ["Fiber"]),
    ("Soy chunks", "RECOMMENDED_FOR", ["Plant Protein"]),
    ("Avocado", "RECOMMENDED_FOR", ["MUFA"]),
]

def seed_lipids_data():
    print(f"🔌 Connecting to Neo4j at {NEO4J_URI}...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))

    with driver.session() as session:
        print("🏥 Creating 'Hyperlipidemia' Condition Node...")
        session.run("MERGE (c:Condition {name: 'Hyperlipidemia'})")

        for food_name, rel_type, nutrients in lipids_data:
            print(f"   -> Processing: {food_name} ({rel_type})")
            query = f"""
            MERGE (f:Food {{name: $food_name}})
            MERGE (c:Condition {{name: 'Hyperlipidemia'}})
            WITH f, c
            FOREACH (nut IN $nutrients | 
                MERGE (n:Nutrient {{name: nut}})
                MERGE (f)-[:HAS_NUTRIENT]->(n)
            )
            MERGE (f)-[:{rel_type}]->(c)
            """
            session.run(query, food_name=food_name, nutrients=nutrients)

    driver.close()
    print("✅ Lipids KG Population Complete!")

if __name__ == "__main__":
    seed_lipids_data()