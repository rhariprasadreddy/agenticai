FROM python:3.11-slim
WORKDIR /app
RUN pip install fastapi uvicorn pydantic requests
COPY ./app /app/app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9004"]