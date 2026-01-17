
#!/bin/bash

# Host IP
HOST="http://192.168.2.69"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}==== 📚 DIRECT RAG (MEMORY) DIAGNOSTIC ====${NC}"
echo "Testing the Knowledge Retrieval Services directly..."

test_rag() {
    NAME=$1
    PORT=$2
    QUERY=$3

    echo -e "\n${GREEN}---- Testing $NAME RAG (Port $PORT) ----${NC}"
    # The endpoint is usually /search, /query, or /retrieve depending on your RAG implementation.
    # We will try /search first, which is standard for many RAGs.
    # If your RAG uses a different endpoint (like /chat or /rag), update this line.
    
    ENDPOINT="/search"
    
    RESPONSE=$(curl -s -m 5 -X POST "$HOST:$PORT$ENDPOINT" \
      -H "Content-Type: application/json" \
      -d "{\"query\": \"$QUERY\", \"top_k\": 2}")

    # Check if curl failed entirely
    if [ -z "$RESPONSE" ]; then
         echo -e "${RED}[FAIL] Connection Refused or Timeout.${NC}"
    else
         # Check if we got a valid JSON list or object back
         if echo "$RESPONSE" | grep -q "doc"; then
             echo -e "${GREEN}[PASS] Retrieved Knowledge Documents:${NC}"
             echo "$RESPONSE" | jq . 2>/dev/null | head -n 10
             echo "... (truncated)"
         else
             echo -e "${RED}[WARN] Unexpected Response format:${NC}"
             echo "$RESPONSE"
         fi
    fi
}

# 1. Diabetes RAG (Port 9101)
test_rag "DIABETES" "9101" "HbA1c targets for elderly"

# 2. Lipids RAG (Port 9102)
test_rag "LIPIDS" "9102" "Foods to lower LDL cholesterol"

# 3. Hypertension RAG (Port 9103)
test_rag "HYPERTENSION" "9103" "DASH diet sodium limits"

# 4. Kidney RAG (Port 9104)
test_rag "KIDNEY" "9104" "Potassium in bananas for CKD"

echo -e "\n${BLUE}==== RAG Diagnostic Complete ====${NC}"
