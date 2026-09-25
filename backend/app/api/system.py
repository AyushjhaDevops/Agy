from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.schemas.system import HealthResponse, RuntimeConfigResponse

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        environment=settings.environment,
    )


@router.get("/api/v1/config", response_model=RuntimeConfigResponse)
def runtime_config(
    settings: Settings = Depends(get_settings),
) -> RuntimeConfigResponse:
    return RuntimeConfigResponse(
        app_name=settings.app_name,
        environment=settings.environment,
        ollama_base_url=settings.ollama_base_url,
        ollama_model=settings.ollama_model,
    )
