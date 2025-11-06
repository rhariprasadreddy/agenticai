import os

ORCH_URL = os.getenv("ORCH_URL", "http://mcp-orchestrator:8081")  # orchestrator stub
API_KEY = os.getenv("API_KEY", "dev-key")
SERVICE_NAME = os.getenv("SERVICE_NAME", "mcp-gateway")
