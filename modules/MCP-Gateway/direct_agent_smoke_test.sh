#!/bin/bash

# Your Host IP
HOST="http://192.168.2.69"

# Colors for readability
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}==== 🕵️  DIRECT AGENT DIAGNOSTIC TOOL ====${NC}"
echo "Bypassing Orchestrator... connecting to ports directly."

# Function to test generic text-generation agents (Hypertension, Kidney, Diabetes)
test_gen_agent() {
    NAME=$1
    PORT=$2
    ENDPOINT=$3
    PROMPT=$4

    echo -e "\n${GREEN}---- Testing $NAME (Port $PORT) ----${NC}"
    echo "Endpoint: $HOST:$PORT$ENDPOINT"
    
    # We use a timeout (-m 10) so we don't hang forever if the agent is dead
    RESPONSE=$(curl -s -m 20 -X POST "$HOST:$PORT$ENDPOINT" \
      -H "Content-Type: application/json" \
      -d "{\"prompt\": \"$PROMPT\", \"max_new_tokens\": 150}")

    if [ -z "$RESPONSE" ]; then
        echo -e "${RED}[FAIL] No response or Timeout.${NC}"
    else
        echo -e "${BLUE}[RAW RESPONSE]${NC}"
        echo "$RESPONSE" | jq . 2>/dev/null || echo "$RESPONSE"
    fi
}

# Function to test the specialized Lipids agent (Strict JSON Schema)
test_lipids_agent() {
    NAME="LIPIDS"
    PORT="9006"
    ENDPOINT="/v1/lipids/plan"

    echo -e "\n${GREEN}---- Testing $NAME (Port $PORT) ----${NC}"
    echo "Endpoint: $HOST:$PORT$ENDPOINT"

    # Lipids requires specific medical fields, not just a "prompt"
    PAYLOAD='{
        "age": 45,
        "sex": "male",
        "ldl": 180,
        "hdl": 35,
        "tg": 220,
        "comorbidities": ["Hypertension"],
        "notes": "Strict Vegetarian"
    }'

    RESPONSE=$(curl -s -m 20 -X POST "$HOST:$PORT$ENDPOINT" \
      -H "Content-Type: application/json" \
      -d "$PAYLOAD")

    if [ -z "$RESPONSE" ]; then
        echo -e "${RED}[FAIL] No response or Timeout.${NC}"
    else
        echo -e "${BLUE}[RAW RESPONSE]${NC}"
        echo "$RESPONSE" | jq . 2>/dev/null || echo "$RESPONSE"
    fi
}

# ==========================================
# 1. Test DIABETES (Port 8080)
# ==========================================
# Assuming Diabetes follows the /generate pattern. If it fails 404, we might need /chat
test_gen_agent "DIABETES" "8080" "/generate" "I have type 2 diabetes. Suggest a breakfast."

# ==========================================
# 2. Test HYPERTENSION (Port 8082)
# ==========================================
test_gen_agent "HYPERTENSION" "8082" "/generate" "My BP is 150/90. Suggest a lunch."

# ==========================================
# 3. Test KIDNEY (Port 9008)
# ==========================================
test_gen_agent "KIDNEY" "9008" "/generate" "Is spinach safe for CKD stage 3?"

# ==========================================
# 4. Test LIPIDS (Port 9006)
# ==========================================
test_lipids_agent

echo -e "\n${BLUE}==== Diagnostic Complete ====${NC}"
