#!/bin/bash
LLM_HOST="192.168.2.69:8080"

echo "🔎 PROBING LLM SERVER AT $LLM_HOST..."

echo -n "1. Checking /v1/models (OpenAI Standard)... "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://$LLM_HOST/v1/models)
if [ "$HTTP_CODE" == "200" ]; then
    echo "✅ FOUND!"
    curl -s http://$LLM_HOST/v1/models | python3 -m json.tool
else
    echo "❌ Failed (Code: $HTTP_CODE)"
fi

echo ""
echo -n "2. Checking /generate (TGI/Plain)... "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://$LLM_HOST/generate -d '{"inputs":"test"}')
if [ "$HTTP_CODE" != "404" ]; then
    echo "✅ FOUND! (Code: $HTTP_CODE)"
else
    echo "❌ Failed (Code: $HTTP_CODE)"
fi

echo ""
echo -n "3. Checking Root /docs... "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://$LLM_HOST/docs)
if [ "$HTTP_CODE" == "200" ]; then
    echo "✅ FOUND!"
else
    echo "❌ Failed (Code: $HTTP_CODE)"
fi
