FROM python:3.11-slim

# Minimal system deps (faiss-cpu wheels usually work without build tools, but curl is handy)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install deps
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy all your service folders into the image
COPY rag-diabetes /app/rag-diabetes
COPY rag-hypertension /app/rag-hypertension
COPY rag-kidney /app/rag-kidney
COPY kg-diabetes /app/kg-diabetes

ENV PYTHONUNBUFFERED=1

