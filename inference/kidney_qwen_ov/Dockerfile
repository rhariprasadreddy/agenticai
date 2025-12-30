FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY ov_kidney_service.py .

# Model directory inside the container (will be mounted from host)
ENV KIDNEY_MODEL_DIR=/models/qwen2.5-1.5b-kidney-ov

# Expose service port
EXPOSE 9008

CMD ["uvicorn", "ov_kidney_service:app", "--host", "0.0.0.0", "--port", "9008"]

