import os

import httpx


def get_api_health() -> dict[str, str]:
    base_url = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
    response = httpx.get(f"{base_url}/api/v1/health", timeout=5.0)
    response.raise_for_status()
    return response.json()
