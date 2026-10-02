import json
from typing import AsyncIterator

import httpx

from .base import LLMError, LLMProvider, LLMRetryable


class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str, model: str, num_ctx: int = 4096,
                 temperature: float = 0.2, keep_alive: str = "30m"):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.num_ctx = num_ctx
        self.temperature = temperature
        self.keep_alive = keep_alive
        # CPU inference is slow: long read timeout, short connect timeout.
        self._timeout = httpx.Timeout(600.0, connect=5.0)

    def _payload(self, system: str, user: str, json_mode: bool, stream: bool) -> dict:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": stream,
            "keep_alive": self.keep_alive,
            "options": {"num_ctx": self.num_ctx, "temperature": self.temperature,"num_predict": 1200},
        }
        if json_mode:
            payload["format"] = "json"
        return payload

    async def generate(self, system: str, user: str, json_mode: bool = False) -> str:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                r = await client.post(
                    f"{self.base_url}/api/chat",
                    json=self._payload(system, user, json_mode, False),
                )
                r.raise_for_status()
                return r.json()["message"]["content"]
        except httpx.ConnectError as e:
            raise LLMError("Cannot reach Ollama. Is it running?") from e
        except httpx.TimeoutException as e:
            raise LLMError("The model took too long to respond.") from e
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 500 and "repeat" in e.response.text:
                 raise LLMRetryable("The model got stuck repeating itself.") from e
            raise LLMError(f"Ollama error {e.response.status_code}: {e.response.text}") from e

    async def stream(self, system: str, user: str) -> AsyncIterator[str]:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json=self._payload(system, user, False, True),
                ) as r:
                    if r.status_code != 200:
                        body = (await r.aread()).decode(errors="replace")
                        raise LLMError(f"Ollama error {r.status_code}: {body}")
                    async for line in r.aiter_lines():
                        if not line:
                            continue
                        data = json.loads(line)
                        chunk = data.get("message", {}).get("content", "")
                        if chunk:
                            yield chunk
                        if data.get("done"):
                            break
        except httpx.ConnectError as e:
            raise LLMError("Cannot reach Ollama. Is it running?") from e
        except httpx.TimeoutException as e:
            raise LLMError("The model took too long to respond.") from e

    async def health(self) -> dict:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                r = await client.get(f"{self.base_url}/api/tags")
                r.raise_for_status()
                names = [m["name"] for m in r.json().get("models", [])]
        except httpx.HTTPError:
            return {"ok": False, "model_installed": False}
        installed = self.model in names or f"{self.model}:latest" in names
        return {"ok": True, "model_installed": installed}