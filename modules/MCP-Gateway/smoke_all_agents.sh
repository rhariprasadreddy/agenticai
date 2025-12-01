#!/bin/bash

GATEWAY="http://localhost:8080"
KEY="dev-key"

echo "==== 🩵 MCP Gateway Smoke Test ===="

test_agent() {
  NAME=$1
  MSG=$2

  echo ""
  echo "---- Testing $NAME ----"
  curl -s -X POST "$GATEWAY/chat" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $KEY" \
    -d "{\"message\": \"$MSG\"}" | jq
}

test_agent "DIABETES"     "I have type 2 diabetes. Give me a one-day Indian vegetarian meal plan."
test_agent "HYPERTENSION" "My BP is 150/95. Suggest a strict DASH diet meal plan."
test_agent "KIDNEY"       "I have CKD stage 3. Is it safe to eat tomatoes daily?"
test_agent "LIPIDS"       "My LDL is 170 and triglycerides 200. What should I change in my diet?"

echo ""
echo "==== 🩵 Smoke Test Complete ===="

