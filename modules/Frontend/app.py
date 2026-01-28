import streamlit as st
import requests

# CONFIG: Clean URL handling
ORCHESTRATOR_URL = "http://192.168.2.57:8081".strip()

st.set_page_config(page_title="AI Clinical Dietitian", layout="wide")
st.title("🥗 Agentic AI Clinical Dietitian")

with st.sidebar:
    st.header("Patient Profile")
    patient_id = st.text_input("Patient ID", "patient_001")
    age = st.number_input("Age", 20, 100, 55)
    gender = st.selectbox("Gender", ["Male", "Female", "Other"])
    
    # Location Selector
    location = st.selectbox("Location", ["Singapore", "India", "USA"])
    
    st.subheader("Clinical Data")
    
    disease_options = [
        "Type 2 Diabetes", 
        "Hypertension", 
        "Chronic Kidney Disease", 
        "High Cholesterol", 
        "Gout", "Celiac Disease", "IBS", "Obesity"
    ]
    
    # Multi-Select Dropdown
    selected_ailments = st.multiselect(
        "Diagnosed Ailments", 
        disease_options,
        default=["Type 2 Diabetes"]
    )
    
    meds_input = st.text_area("Medications (comma separated)", "Metformin, Lisinopril")
    
    st.markdown("---")
    user_query = st.text_area("Request", "Generate a safe meal plan for me.")
    generate_btn = st.button("Generate Plan", type="primary")

if generate_btn:
    # --- FIX APPLIED HERE: COMBINE LIST INTO STRING ---
    conditions_str = ", ".join(selected_ailments) if selected_ailments else "General"
    
    payload = {
        "patient_id": patient_id,
        "age": age,
        "gender": gender,
        "location": location,
        "medical_record": {
            "condition": conditions_str,  # Now sends "Diabetes, Kidney"
            "current_meds": [m.strip() for m in meds_input.split(",") if m.strip()]
        },
        "user_query": user_query
    }
    
    st.info(f"Contacting Orchestrator at {ORCHESTRATOR_URL}...")
    
    try:
        full_url = f"{ORCHESTRATOR_URL}/run-pipeline"
        response = requests.post(full_url, json=payload, timeout=120)
        
        if response.status_code == 200:
            data = response.json()
            meal_plan = data.get("meal_plan", {})
            warnings = data.get("warnings", [])

            # 1. DISPLAY SAFETY WARNINGS
            if warnings:
                st.error("🚨 CLINICAL SAFETY ALERTS")
                for w in warnings: st.write(w)
                st.divider()
            else:
                st.success("✅ Clinical Checks Passed: No contraindicated foods detected.")

            # 2. RENDER MEAL PLAN
            st.subheader("Recommended Meal Plan")
            if isinstance(meal_plan, dict) and any(k in meal_plan for k in ["breakfast", "lunch", "dinner"]):
                tab1, tab2, tab3 = st.tabs(["🍳 Breakfast", "🥗 Lunch", "🍲 Dinner"])
                with tab1: st.json(meal_plan.get("breakfast", "No data"))
                with tab2: st.json(meal_plan.get("lunch", "No data"))
                with tab3: st.json(meal_plan.get("dinner", "No data"))
            else:
                st.json(meal_plan)

            # Debug Section
            with st.expander("Show Full System Debug"):
                st.json(data)
        else:
            st.error(f"Error {response.status_code}: {response.text}")
            
    except Exception as e:
        st.error(f"Connection Failed: {e}")