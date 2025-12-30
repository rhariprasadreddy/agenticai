FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ov_htn_service.py /app/ov_htn_service.py

EXPOSE 8082

CMD ["uvicorn", "ov_htn_service:app", "--host", "0.0.0.0", "--port", "8082"]
