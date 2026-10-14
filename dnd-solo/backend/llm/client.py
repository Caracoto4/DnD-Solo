"""Клиент koboldcpp (OpenAI-совместимый /v1/chat/completions) с retry."""
from __future__ import annotations

import asyncio
import logging

import httpx

log = logging.getLogger("llm.client")


class LLMError(RuntimeError):
    pass


class KoboldClient:
    def __init__(self, endpoint: str, model: str = "", temperature: float = 0.88,
                 max_tokens: int = 1024, timeout: float = 120.0):
        self.endpoint = endpoint
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

    async def chat(self, messages: list[dict[str, str]]) -> str:
        """Отправляет messages, возвращает content первого choice.

        Retries: 3 попытки с exponential backoff при сетевых ошибках / 5xx.
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        last_err: Exception | None = None
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(3):
                try:
                    r = await client.post(self.endpoint, json=payload)
                    if r.status_code >= 500:
                        raise LLMError(f"koboldcpp вернул {r.status_code}: {r.text[:200]}")
                    r.raise_for_status()
                    data = r.json()
                    return data["choices"][0]["message"]["content"]
                except (httpx.HTTPError, KeyError, IndexError, ValueError) as e:
                    last_err = e
                    wait = 2 ** attempt
                    log.warning("LLM attempt %d failed: %s; retry in %ss", attempt + 1, e, wait)
                    await asyncio.sleep(wait)
        raise LLMError(f"Не удалось получить ответ от koboldcpp: {last_err}")

    async def health(self) -> bool:
        """Проверка доступности: GET /v1/models на том же хосте."""
        try:
            base = self.endpoint.split("/v1/")[0]
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{base}/v1/models")
                return r.status_code == 200
        except httpx.HTTPError:
            return False
