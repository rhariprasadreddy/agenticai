#!/bin/bash
echo "=== 1. CHECKING LOCAL CONTAINERS ==="
CONTAINERS=("orchestrator" "mcp-gateway" "agent-a1" "agent-a2" "agent-a3" "agent-a4" "agent-a5")

for container in "${CONTAINERS[@]}"; do
    if docker ps --format '{{.Names}}' | grep -q "$container"; then
        echo "[$container]: RUNNING"
    else
        echo "[$container]: 🔴 STOPPED/MISSING"
    fi
done

echo ""
echo "=== 2. CHECKING AGENT HEALTH (HTTP PING) ==="
# We assume localhost because we are running this ON the server
curl -s -o /dev/null -w "[Orchestrator] Port 8081: %{http_code}\n" http://localhost:8081/docs || echo "[Orchestrator] Port 8081: 🔴 UNREACHABLE"
curl -s -o /dev/null -w "[A1-Rules] Port 9001: %{http_code}\n" http://localhost:9001/docs || echo "[A1-Rules] Port 9001: 🔴 UNREACHABLE"
curl -s -o /dev/null -w "[A2-Gaps] Port 9002: %{http_code}\n" http://localhost:9002/docs || echo "[A2-Gaps] Port 9002: 🔴 UNREACHABLE"
curl -s -o /dev/null -w "[A3-Targets] Port 9003: %{http_code}\n" http://localhost:9003/docs || echo "[A3-Targets] Port 9003: 🔴 UNREACHABLE"
curl -s -o /dev/null -w "[A4-Conflicts] Port 9004: %{http_code}\n" http://localhost:9004/docs || echo "[A4-Conflicts] Port 9004: 🔴 UNREACHABLE"
curl -s -o /dev/null -w "[A5-Planner] Port 9005: %{http_code}\n" http://localhost:9005/docs || echo "[A5-Planner] Port 9005: 🔴 UNREACHABLE"

echo ""
echo "=== 3. CHECKING REMOTE INFERENCE SERVER ==="
# Adjust IP if needed
REMOTE_IP="192.168.2.69" 
if ping -c 1 -W 1 "$REMOTE_IP" &> /dev/null; then
    echo "Remote Server ($REMOTE_IP): ONLINE"
    curl -s -o /dev/null -w "LLM Service (8080): %{http_code}\n" http://$REMOTE_IP:8080/docs || echo "LLM Service: 🔴 UNREACHABLE"
else
    echo "Remote Server ($REMOTE_IP): 🔴 OFFLINE"
fi

echo ""
echo "=== DIAGNOSTIC COMPLETE ==="
