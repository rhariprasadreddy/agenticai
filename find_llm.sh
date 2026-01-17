#!/bin/bash
LLM_HOST="192.168.2.69:8080"
echo "🔎 PROBING LLM SERVER AT $LLM_HOST..."

# Check 1: OpenAI Standard Path
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://$LLM_HOST/v1/models)
if [ "$HTTP_CODE" == "200" ]; then
    echo "✅ FOUND! Path is /v1/models"
    echo "📋 Model Name:"
    curl -s http://$LLM_HOST/v1/models | python3 -m json.tool
else
    echo "❌ /v1/models Failed (Code: $HTTP_CODE)"
fi

# Check 2: TGI Path
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://$LLM_HOST/generate -d '{"inputs":"test"}')
if [ "$HTTP_CODE" != "404" ] && [ "$HTTP_CODE" != "000" ]; then
    echo "✅ FOUND! Path is /generate"
fi
