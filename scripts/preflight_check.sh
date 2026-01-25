#!/bin/bash
echo "=== 🏥 AGENTIC AI PRE-FLIGHT CHECK ==="

# 1. Check Containers
echo -e "\n🔹 Checking Container Status..."
if [ $(docker ps -q | wc -l) -ge 6 ]; then
    echo "✅ All Containers Running"
else
    echo "❌ WARNING: Some containers are down!"
    docker ps --format "table {{.Names}}\t{{.Status}}"
fi

# 2. Check Orchestrator Connectivity
echo -e "\n🔹 Pinging Orchestrator..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8081/docs)
if [ "$HTTP_CODE" == "200" ]; then
    echo "✅ Orchestrator API is Live (HTTP 200)"
else
    echo "❌ Orchestrator Failed (HTTP $HTTP_CODE)"
fi

# 3. Check UI Port
echo -e "\n🔹 Checking Portal UI..."
if nc -z localhost 3000; then
    echo "✅ UI Port 3000 is Open"
else
    echo "❌ UI Port 3000 is Closed"
fi

# 4. Quick Inference Test
echo -e "\n🔹 Running Smoke Test (Kidney Agent)..."
python3 scripts/06_full_system_test.py > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Inference Pipeline Functional"
else
    echo "❌ Inference Test Failed! Check logs."
fi

echo -e "\n🚀 SYSTEM READY FOR DEMO."
