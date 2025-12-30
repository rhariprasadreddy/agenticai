FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Remove hardcoded model paths from here. 
# We will pass them at runtime.

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN python3 -m pip install --upgrade pip && \
    python3 -m pip install -r /app/requirements.txt

COPY ov_diabetes_service.py /app/ov_diabetes_service.py

EXPOSE 8080

# Default command (can be overridden)
CMD ["uvicorn", "ov_diabetes_service:app", "--host", "0.0.0.0", "--port", "8080"]
