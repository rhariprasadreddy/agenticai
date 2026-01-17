#!/usr/bin/env python3
import os
from neo4j import GraphDatabase

# Config
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://192.168.2.69:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASS", "neo4j123")

# DATA: Kidney (CKD Stage 3+) Knowledge Base
# Focus: Potassium, Phosphorus, Sodium, Protein quality
kidney_data = [
    # ❌ AVOID / HIGH RISK
    ("Spinach", "AVOID_FOR", ["Potassium"]), 
    ("Banana", "AVOID_FOR", ["Potassium"]),
    ("Potatoes", "AVOID_FOR", ["Potassium"]),
    ("Tomatoes", "AVOID_FOR", ["Potassium"]),
    ("Coconut Water", "AVOID_FOR", ["Potassium"]),
    ("Canned Soup", "AVOID_FOR", ["Sodium", "Preservatives"]),
    ("Pickles", "AVOID_FOR", ["Sodium"]),
    ("Colas", "AVOID_FOR", ["Phosphorus"]), # Dark sodas are bad
    ("Processed Cheese", "AVOID_FOR", ["Phosphorus", "Sodium"]),
    ("Chocolate", "AVOID_FOR", ["Phosphorus"]),

    # ⚠️ LIMIT (Needs leaching or portion control)
    ("Toor Dal", "LIMIT_FOR", ["Potassium", "Phosphorus"]),
    ("Dairy Milk", "LIMIT_FOR", ["Phosphorus"]),
    ("Nuts", "LIMIT_FOR", ["Phosphorus"]),
    ("Whole Wheat Bread", "LIMIT_FOR", ["Phosphorus"]), # White often better for phos absorption
    ("Brown Rice", "LIMIT_FOR", ["Phosphorus"]),

    # ✅ RECOMMENDED / LOW RISK
    ("Egg Whites", "RECOMMENDED_FOR", ["High Quality Protein"]), # Low phos compared to yolk
    ("Cauliflower", "RECOMMENDED_FOR", ["Low Potassium"]),
    ("Cabbage", "RECOMMENDED_FOR", ["Low Potassium"]),
    ("Bottle Gourd (Lauki)", "RECOMMENDED_FOR", ["Low Potassium"]),
    ("White Rice", "RECOMMENDED_FOR", ["Low Phosphorus"]),
    ("Apples", "RECOMMENDED_FOR", ["Fiber"]),
    ("Guava", "RECOMMENDED_FOR", ["Fiber"]),
    ("Paneer", "LIMIT_FOR", ["Phosphorus"]), # Ok in moderation if leached
]

def seed_kidney_data():
    print(f"🔌 Connecting to Neo4j at {NEO4J_URI}...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))

    with driver.session() as session:
        print("🏥 Creating 'CKD' Condition Node...")
        session.run("MERGE (c:Condition {name: 'CKD'})")

        for food_name, rel_type, nutrients in kidney_data:
            print(f"   -> Processing: {food_name} ({rel_type})")
            query = f"""
            MERGE (f:Food {{name: $food_name}})
            MERGE (c:Condition {{name: 'CKD'}})
            WITH f, c
            FOREACH (nut IN $nutrients | 
                MERGE (n:Nutrient {{name: nut}})
                MERGE (f)-[:HAS_NUTRIENT]->(n)
            )
            MERGE (f)-[:{rel_type}]->(c)
            """
            session.run(query, food_name=food_name, nutrients=nutrients)

    driver.close()
    print("✅ Kidney KG Population Complete!")

if __name__ == "__main__":
    seed_kidney_data()