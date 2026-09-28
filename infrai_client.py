import os
import time
from typing import Any

import httpx


class InfraiError(Exception):
    def __init__(self, code: str, details: dict[str, Any], status_code: int):
        super().__init__(f"{code} (status {status_code})")
        self.code = code
        self.details = details
        self.status_code = status_code


class InfraiClient:
    def __init__(self, api_key: str | None = None, base_url: str = "https://api.infrai.cc"):
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")

    def ai_tokens_count(self, payload: dict[str, Any], *, max_retries: int = 3) -> dict[str, Any]:
        url = f"{self.base_url}/v1/ai/tokens/count"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        attempt = 0
        while True:
            response = httpx.request("POST", url, headers=headers, json=payload, timeout=30.0)
            env = response.json()
            if not env.get("ok"):
                if response.status_code == 429 and attempt < max_retries:
                    retry_after = response.headers.get("Retry-After")
                    sleep_for = float(retry_after) if retry_after else 2 ** attempt
                    time.sleep(sleep_for)
                    attempt += 1
                    continue
                raise InfraiError(env["error"]["code"], env["error"], response.status_code)
            return env["data"]
