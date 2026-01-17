FROM python:3.11-slim
WORKDIR /app

# Install Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Code
COPY app ./app

# Run Uvicorn
# We use --host 0.0.0.0 so Docker can map the port
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9005"]
