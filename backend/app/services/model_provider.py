from dataclasses import dataclass
from typing import AsyncIterator, Protocol


class ModelProviderError(Exception):
    """Base error for local model provider failures."""


class ProviderUnavailableError(ModelProviderError):
    pass


class ModelNotFoundError(ModelProviderError):
    pass


class ModelProvider(Protocol):
    async def generate(self, prompt: str, model: str | None = None) -> str: ...

    async def stream(self, prompt: str, model: str | None = None) -> AsyncIterator[str]: ...

    async def health(self) -> bool: ...

    async def list_models(self) -> list[str]: ...


@dataclass(frozen=True)
class ProviderHealth:
    available: bool
    models: list[str]
