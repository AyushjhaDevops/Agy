from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str


class RuntimeConfigResponse(BaseModel):
    app_name: str
    environment: str
    ollama_base_url: str
    ollama_model: str
