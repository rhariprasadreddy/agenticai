#!/bin/bash

# Define colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "==== 🔍 STARTING PRE-FLIGHT CHECK ===="
echo -e "Checking files relative to: $(pwd)"
echo "----------------------------------------"

# Function to check file existence
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}[OK]${NC} Found Code: $1"
    else
        echo -e "${RED}[FAIL]${NC} MISSING Code: $1"
    fi
}

# Function to check model directory and XML file
check_model() {
    if [ -d "$1" ]; then
        if [ -f "$1/openvino_model.xml" ]; then
            echo -e "${GREEN}[OK]${NC} Found Model: $1 (Contains openvino_model.xml)"
        else
            echo -e "${YELLOW}[WARN]${NC} Folder exists but NO 'openvino_model.xml' in: $1"
            # List what is there to help debug
            ls "$1"
        fi
    else
        echo -e "${RED}[FAIL]${NC} MISSING Model Folder: $1"
    fi
}

# 1. CHECK PYTHON SERVICE FILES (Based on your Tree output)
echo -e "\n--- Checking Inference Codes ---"
# Diabetes
check_file "./inference/diabetes_qwen_ov/ov_diabetes_service.py"

# Hypertension (Note: Your tree said 'ov_hypertension_service.py' but runlike said 'ov_htn_service.py'. Checking both)
if [ -f "./inference/hypertension_qwen_ov/ov_hypertension_service.py" ]; then
     echo -e "${GREEN}[OK]${NC} Found Code: ./inference/hypertension_qwen_ov/ov_hypertension_service.py"
elif [ -f "./services/ov_htn_service.py" ]; then
     echo -e "${YELLOW}[WARN]${NC} Found old path './services/ov_htn_service.py'. Update your Docker Compose to match this!"
else
     echo -e "${RED}[FAIL]${NC} Could not find Hypertension service file!"
fi

# Kidney
check_file "./inference/kidney_qwen_ov/ov_kidney_service.py"

# Lipids
check_file "./inference/lipids_qwen_ov/ov_lipids_service.py"


# 2. CHECK MODEL DIRECTORIES (Standardized Structure)
echo -e "\n--- Checking Standardized Model Folders ---"
check_model "./models/openvino/diabetes/fp16"
check_model "./models/openvino/hypertension/fp16"
check_model "./models/openvino/kidney/fp16"
check_model "./models/openvino/lipids/fp16"

echo "----------------------------------------"
echo -e "If you see any ${RED}[FAIL]${NC}, run the 'mkdir' and 'cp' commands I gave earlier."
echo -e "If you see ${YELLOW}[WARN]${NC}, update your docker-compose.yaml path to match the actual file."
