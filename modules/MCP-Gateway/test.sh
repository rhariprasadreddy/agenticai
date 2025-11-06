curl -X POST http://localhost:8080/v1/cases \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-key" \
  -d '{
    "version":"v1",
    "patient_id":"P123456",
    "age": 58,
    "sex":"male",
    "bmi":27.3,
    "activity":"light",
    "culture":"south-indian",
    "locale":"SG",
    "budget": 15.0,
    "diagnoses_icd":["E11.9","I10"],
    "medications":["metformin","amlodipine"],
    "allergies":["penicillin"],
    "labs":{"hbA1c":7.2,"creatinine":1.6}
  }'
# -> {"status":"accepted","schema":"Profile.v1"}
