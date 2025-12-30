FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Optional but recommended: system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY requirements.txt /app/requirements.txt
RUN python3 -m pip install --upgrade pip && \
    python3 -m pip install -r /app/requirements.txt

# Copy service script
COPY ov_lipids_service.py /app/ov_lipids_service.py

# Default port for Lipids agent
EXPOSE 9006

# ENV for model path inside container (we'll mount it from host)
ENV LIPIDS_OV_DIR=/models/openvino/lipids/bf16

# Launch FastAPI with uvicorn
CMD ["uvicorn", "ov_lipids_service:app", "--host", "0.0.0.0", "--port", "9006"]

