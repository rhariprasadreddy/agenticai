#!/bin/bash
# File: ~/agenticai/modules/check_infrastructure_status.sh

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== 1. CHECKING LOCAL CONTAINERS ===${NC}"
# Check if essential containers are running
for container in orchestrator mcp-gateway agent-a1 agent-a2 agent-a3 agent-a4 agent-a5; do
    if [ "$(docker ps -q -f name=$container)" ]; then
        echo -e "[$container]: ${GREEN}RUNNING${NC}"
    else
        echo -e "[$container]: ${RED}STOPPED/MISSING${NC}"
    fi
done

echo -e "\n${GREEN}=== 2. CHECKING AGENT HEALTH (HTTP PING) ===${NC}"
# A quick ping to the root or health endpoint of each agent
agents=(
    "Orchestrator:8081"
    "A1-Rules:9001"
    "A2-Gaps:9002"
    "A3-Targets:9003"
    "A4-Conflicts:9004"
    "A5-Planner:9005"
)

for agent in "${agents[@]}"; do
    name="${agent%%:*}"
    port="${agent##*:}"
    # Use timeout to avoid hanging
    curl --max-time 2 -s "http://localhost:$port/docs" > /dev/null
    if [ $? -eq 0 ]; then
        echo -e "[$name] Port $port: ${GREEN}RESPONDING${NC}"
    else
        echo -e "[$name] Port $port: ${RED}NO RESPONSE${NC}"
    fi
done

echo -e "\n${GREEN}=== 3. CHECKING REMOTE INFERENCE SERVER ===${NC}"
REMOTE_IP="192.168.2.69"
REMOTE_PORT="8080" # Assuming OPEA/vLLM is on 8080

# Simple connectivity check
if ping -c 1 -W 1 $REMOTE_IP &> /dev/null; then
    echo -e "Remote Server ($REMOTE_IP): ${GREEN}ONLINE (Ping Success)${NC}"
    
    # Check if the LLM port is open
    curl --max-time 2 -s "http://$REMOTE_IP:$REMOTE_PORT/health" > /dev/null
    # Note: Depending on the inference server, /health might not exist, 
    # but a connection refusal is distinct from a 404.
    if [ $? -eq 0 ] || [ $? -eq 22 ]; then # 22 is sometimes 404/405 which means server is up
        echo -e "LLM Service ($REMOTE_PORT): ${GREEN}REACHABLE${NC}"
    else
        echo -e "LLM Service ($REMOTE_PORT): ${RED}UNREACHABLE${NC}"
    fi
else
    echo -e "Remote Server ($REMOTE_IP): ${RED}OFFLINE${NC}"
fi

echo -e "\n${GREEN}=== DIAGNOSTIC COMPLETE ===${NC}"
