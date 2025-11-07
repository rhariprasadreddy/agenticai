#!/usr/bin/env bash
set -e
echo "[1] Orchestrator health:"
curl -s http://localhost:8081/health | jq
echo "[2] Create case via Gateway:"
curl -s -X POST http://localhost:8080/v1/cases \
  -H "Content-Type: application/json" -H "x-api-key: dev-key" \
  -d '{"version":"v1","patient_id":"P12345","age":60,"sex":"female","bmi":28.5,"diagnoses_icd":["E11.9"],"activity":"light","culture":"south-indian","locale":"SG","budget":12.5}' | jq
echo "[3] Fetch plan via Gateway:"
curl -s http://localhost:8080/v1/cases/P12345/plan -H "x-api-key: dev-key" | jq
