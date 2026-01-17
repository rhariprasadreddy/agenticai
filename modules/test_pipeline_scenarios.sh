#!/bin/bash

# Configuration
URL="http://localhost:8081/run-pipeline"
separator="--------------------------------------------------------------------------------"

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}Starting Multi-Agent Pipeline Stress Test...${NC}"
echo "Target: $URL"
echo $separator

# Function to send request
run_test() {
    local test_name="$1"
    local json_payload="$2"

    echo -e "${YELLOW}Running Test: $test_name${NC}"
    
    # Send Request and capture response
    response=$(curl -s -X POST "$URL" \
        -H "Content-Type: application/json" \
        -d "$json_payload")

    # Check if curl failed
    if [ $? -ne 0 ]; then
        echo -e "${RED}Request Failed!${NC}"
        return
    fi

    # Parse and Display Logic (using jq)
    # extracting Plan and Safety Notes
    plan=$(echo "$response" | jq -r '.final_plan')
    safety=$(echo "$response" | jq -r '.safety_notes')
    
    if [ "$plan" == "null" ]; then
        echo -e "${RED}Error in Response:${NC}"
        echo "$response" | jq .
    else
        echo -e "${GREEN}>>> Plan Output:${NC}"
        echo "$plan" | head -n 20  # Print first 20 lines to keep it brief
        echo "..."
        echo -e "${GREEN}>>> Safety Notes:${NC}"
        echo "$safety"
    fi
    echo $separator
    echo ""
    sleep 1 # Pause to be nice to the CPU
}

# ==========================================
# TEST CASE 1: Single Disease (Diabetes) - SG - Male
# ==========================================
run_test "1. Single (Diabetes) - SG - Male" '{
    "patient_id": "case_01", "age": 45, "gender": "male", "location": "Singapore",
    "ailments": ["Type 2 Diabetes"],
    "medical_record": {"condition": "Diabetes", "hba1c": 8.1},
    "query": "I want a hawker centre meal plan."
}'

# ==========================================
# TEST CASE 2: Single Disease (Hypertension) - India - Female
# ==========================================
run_test "2. Single (Hypertension) - India - Female" '{
    "patient_id": "case_02", "age": 60, "gender": "female", "location": "India",
    "ailments": ["Hypertension"],
    "medical_record": {"condition": "High BP", "bp_systolic": 160},
    "query": "Vegetarian indian diet please."
}'

# ==========================================
# TEST CASE 3: Two Diseases (Banana Paradox) - SG - Female
# ==========================================
run_test "3. Dual (Diabetes + HTN) - SG - Female (Banana Check)" '{
    "patient_id": "case_03", "age": 55, "gender": "female", "location": "Singapore",
    "ailments": ["Type 2 Diabetes", "Hypertension"],
    "medical_record": {"current_meds": ["Lisinopril", "Metformin"]},
    "query": "Can I eat bananas for breakfast?"
}'

# ==========================================
# TEST CASE 4: Two Diseases (Deficiency) - India - Male
# ==========================================
run_test "4. Dual (Anemia + Osteoporosis) - India - Male" '{
    "patient_id": "case_04", "age": 70, "gender": "male", "location": "India",
    "ailments": ["Anemia", "Osteoporosis"],
    "medical_record": {"hemoglobin": "low", "bone_density": "low"},
    "query": "Fix my vitamins with food."
}'

# ==========================================
# TEST CASE 5: Three Diseases (Complex) - SG - Male
# ==========================================
run_test "5. Triple (Diabetes + HTN + Kidney) - SG - Male" '{
    "patient_id": "case_05", "age": 65, "gender": "male", "location": "Singapore",
    "ailments": ["Type 2 Diabetes", "Hypertension", "Chronic Kidney Disease"],
    "medical_record": {"creatinine_level": 2.8, "weight_kg": 70},
    "query": "What can I eat safely?"
}'

# ==========================================
# TEST CASE 6: Four Diseases (Stress Test) - India - Female
# ==========================================
run_test "6. Quad (Diabetes + HTN + Kidney + Lipids) - India - Female" '{
    "patient_id": "case_06", "age": 50, "gender": "female", "location": "India",
    "ailments": ["Type 2 Diabetes", "Hypertension", "Chronic Kidney Disease", "High Cholesterol"],
    "medical_record": {"ldl": 190, "creatinine": 2.0},
    "query": "Strict vegetarian plan needed."
}'

# ==========================================
# TEST CASE 7: Medication Conflict (Lisinopril)
# ==========================================
run_test "7. Drug Conflict (Lisinopril + Potassium)" '{
    "patient_id": "case_07", "age": 40, "gender": "male", "location": "Singapore",
    "ailments": ["Hypertension"],
    "medical_record": {"current_meds": ["Lisinopril"]},
    "query": "I love avocado and spinach smoothies."
}'

# ==========================================
# TEST CASE 8: Medication Conflict (Metformin)
# ==========================================
run_test "8. Drug Conflict (Metformin + B12)" '{
    "patient_id": "case_08", "age": 55, "gender": "female", "location": "India",
    "ailments": ["Type 2 Diabetes"],
    "medical_record": {"current_meds": ["Metformin"]},
    "query": "Plan for energy."
}'

# ==========================================
# TEST CASE 9: Baseline (Healthy) - SG
# ==========================================
run_test "9. Baseline (No Ailments) - SG" '{
    "patient_id": "case_09", "age": 25, "gender": "male", "location": "Singapore",
    "ailments": [],
    "medical_record": {},
    "query": "Healthy bulking diet."
}'

# ==========================================
# TEST CASE 10: Kidney Protein Check (Math)
# ==========================================
run_test "10. Kidney Protein Limit Check" '{
    "patient_id": "case_10", "age": 50, "gender": "male", "location": "India",
    "ailments": ["Chronic Kidney Disease"],
    "medical_record": {"condition": "CKD", "weight_kg": 100},
    "query": "I want to eat 150g of protein."
}'

echo -e "${CYAN}All Tests Completed.${NC}"
