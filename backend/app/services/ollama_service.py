import json
from collections.abc import AsyncIterator

import httpx

from app.services.model_provider import (
    ModelNotFoundError,
    ProviderUnavailableError,
)


class OllamaProvider:
    """Async Ollama adapter using the stable local HTTP API."""

    def __init__(self, base_url: str, default_model: str, timeout: float = 120.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model.strip()
        self.timeout = timeout

    async def list_models(self) -> list[str]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
        except (httpx.HTTPError, OSError) as exc:
            raise ProviderUnavailableError("Ollama is unavailable") from exc
        return [item["name"] for item in response.json().get("models", []) if item.get("name")]

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.is_success
        except (httpx.HTTPError, OSError):
            return False

    def _select_model(self, model: str | None) -> str:
        selected = (model or self.default_model).strip()
        if not selected:
            raise ModelNotFoundError("No Ollama model is configured")
        return selected

    async def generate(self, prompt: str, model: str | None = None) -> str:
        selected = self._select_model(model)
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={"model": selected, "prompt": prompt, "stream": False},
                )
                if response.status_code == 404:
                    raise ModelNotFoundError(f"Ollama model not found: {selected}")
                response.raise_for_status()
        except ModelNotFoundError:
            raise
        except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPError, OSError) as exc:
            raise ProviderUnavailableError("Ollama generation failed") from exc
        return response.json().get("response", "")

    async def stream(self, prompt: str, model: str | None = None) -> AsyncIterator[str]:
        selected = self._select_model(model)
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/generate",
                    json={"model": selected, "prompt": prompt, "stream": True},
                ) as response:
                    if response.status_code == 404:
                        raise ModelNotFoundError(f"Ollama model not found: {selected}")
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        payload = json.loads(line)
                        if payload.get("error"):
                            raise ProviderUnavailableError(payload["error"])
                        text = payload.get("response", "")
                        if text:
                            yield text
        except ModelNotFoundError:
            raise
        except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPError, OSError) as exc:
            raise ProviderUnavailableError("Ollama streaming failed") from exc
