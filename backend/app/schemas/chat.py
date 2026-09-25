from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    project_id: str | None = None
    conversation_id: str | None = None
    model: str | None = None


class ChatResponse(BaseModel):
    assistant_message: str
    model: str
    duration: float
    status: str
    conversation_id: str


class ModelListResponse(BaseModel):
    models: list[str]
    available: bool
