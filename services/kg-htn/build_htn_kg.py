#!/usr/bin/env python3
import os
from neo4j import GraphDatabase

# -------------------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------------------
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://192.168.2.69:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASS", "neo4j123") # Update if needed

# -------------------------------------------------------------------
# DATA: Hypertension Knowledge Base (Structured)
# -------------------------------------------------------------------
# Schema: (Food Name, Relationship, List of Nutrients causing this)
htn_data = [
    # ❌ AVOID / STRICT LIMIT
    ("Pickles", "AVOID_FOR", ["Sodium"]),
    ("Papad", "AVOID_FOR", ["Sodium"]),
    ("Canned Soup", "AVOID_FOR", ["Sodium", "Preservatives"]),
    ("Soy Sauce", "AVOID_FOR", ["Sodium"]),
    ("Processed Cheese", "AVOID_FOR", ["Sodium", "Saturated Fat"]),
    ("Baking Soda", "AVOID_FOR", ["Sodium"]),

    # ⚠️ LIMIT
    ("Coconut Oil", "LIMIT_FOR", ["Saturated Fat"]),
    ("Butter", "LIMIT_FOR", ["Saturated Fat"]),
    ("Coffee", "LIMIT_FOR", ["Caffeine"]),

    # ✅ RECOMMENDED (DASH Diet)
    ("Spinach", "RECOMMENDED_FOR", ["Potassium", "Magnesium", "Fiber"]),
    ("Banana", "RECOMMENDED_FOR", ["Potassium"]),
    ("Beetroot", "RECOMMENDED_FOR", ["Nitrates"]),
    ("Low-fat Yogurt", "RECOMMENDED_FOR", ["Calcium", "Protein"]),
    ("Oats", "RECOMMENDED_FOR", ["Fiber"]),
    ("Flax Seeds", "RECOMMENDED_FOR", ["Omega-3"]),
    ("Garlic", "RECOMMENDED_FOR", ["Allicin"]),
    
    # 🆗 OK
    ("Brown Rice", "OK_FOR", ["Fiber"]),
    ("Moong Dal", "OK_FOR", ["Protein"]),
]

def seed_hypertension_data():
    print(f"🔌 Connecting to Neo4j at {NEO4J_URI}...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))

    with driver.session() as session:
        # 1. Ensure the Condition Node exists
        print("🏥 Creating 'Hypertension' Condition Node...")
        session.run("MERGE (c:Condition {name: 'Hypertension'})")

        # 2. Loop through data and create nodes/relationships
        for food_name, rel_type, nutrients in htn_data:
            print(f"   -> Processing: {food_name} ({rel_type})")
            
            # A. Create Food Node
            # B. Create Nutrient Nodes and link to Food
            # C. Create Relationship between Food and Hypertension
            query = f"""
            MERGE (f:Food {{name: $food_name}})
            MERGE (c:Condition {{name: 'Hypertension'}})
            
            // Link Nutrients
            WITH f, c
            FOREACH (nut IN $nutrients | 
                MERGE (n:Nutrient {{name: nut}})
                MERGE (f)-[:HAS_NUTRIENT]->(n)
            )

            // Create Specific Relationship (Dynamic Type)
            MERGE (f)-[:{rel_type}]->(c)
            """
            
            session.run(query, food_name=food_name, nutrients=nutrients)

    driver.close()
    print("✅ Hypertension KG Population Complete!")

if __name__ == "__main__":
    seed_hypertension_data()