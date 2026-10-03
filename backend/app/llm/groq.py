import json
from typing import AsyncIterator

import httpx

from .base import LLMError, LLMProvider, LLMRetryable


class GroqProvider(LLMProvider):
    def __init__(
        self,
        api_key: str,
        model: str = "openai/gpt-oss-20b",
        num_ctx: int = 4096,
        temperature: float = 0.2,
    ):
        self.api_key = api_key
        self.model = model
        self.num_ctx = num_ctx
        self.temperature = temperature

        self.base_url = "https://api.groq.com/openai/v1"
        self._timeout = httpx.Timeout(120.0, connect=10.0)

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _payload(
        self,
        system: str,
        user: str,
        json_mode: bool,
        stream: bool,
    ) -> dict:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": self.temperature,
            "max_tokens": 1200,
            "stream": stream,
        }

        if json_mode:
            payload["response_format"] = {"type": "json_object"}
            payload["include_reasoning"] = False
            payload["reasoning_effort"] = "low"

        return payload

    async def generate(
        self,
        system: str,
        user: str,
        json_mode: bool = False,
    ) -> str:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                r = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(),
                    json=self._payload(
                        system,
                        user,
                        json_mode,
                        False,
                    ),
                )

                if r.status_code == 429:
                    raise LLMRetryable(
                        "The hosted model is temporarily rate limited."
                    )

                r.raise_for_status()

                data = r.json()

                return data["choices"][0]["message"]["content"]

        except httpx.TimeoutException as e:
            raise LLMError(
                "The hosted model took too long to respond."
            ) from e

        except httpx.HTTPStatusError as e:
            raise LLMError(
                f"Groq error {e.response.status_code}: "
                f"{e.response.text}"
            ) from e

    async def stream(
        self,
        system: str,
        user: str,
    ) -> AsyncIterator[str]:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(),
                    json=self._payload(
                        system,
                        user,
                        False,
                        True,
                    ),
                ) as r:

                    if r.status_code == 429:
                        raise LLMRetryable(
                            "The hosted model is temporarily rate limited."
                        )

                    if r.status_code != 200:
                        body = (
                            await r.aread()
                        ).decode(errors="replace")

                        raise LLMError(
                            f"Groq error {r.status_code}: {body}"
                        )

                    async for line in r.aiter_lines():

                        if not line or not line.startswith("data:"):
                            continue

                        data = line[5:].strip()

                        if data == "[DONE]":
                            break

                        chunk = json.loads(data)

                        content = (
                            chunk
                            .get("choices", [{}])[0]
                            .get("delta", {})
                            .get("content", "")
                        )

                        if content:
                            yield content

        except httpx.TimeoutException as e:
            raise LLMError(
                "The hosted model took too long to respond."
            ) from e

    async def health(self) -> dict:
        if not self.api_key:
            return {
                "ok": False,
                "model_installed": False,
            }

        return {
            "ok": True,
            "model_installed": True,
        }