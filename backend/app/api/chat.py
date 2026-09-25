import time

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect

from app.core.config import Settings, get_settings
from app.schemas.chat import ChatRequest, ChatResponse, ModelListResponse
from app.services.conversation_store import ConversationStore
from app.services.model_provider import ModelNotFoundError, ProviderUnavailableError
from app.services.ollama_service import OllamaProvider

router = APIRouter(prefix="/api/v1", tags=["chat"])


def get_provider(settings: Settings = Depends(get_settings)) -> OllamaProvider:
    return OllamaProvider(settings.ollama_base_url, settings.ollama_model, settings.ollama_timeout_seconds)


def get_store(settings: Settings = Depends(get_settings)) -> ConversationStore:
    return ConversationStore(settings.database_url)


def prompt_from_history(messages: list[dict[str, str]], current: str) -> str:
    lines = [f"{item['role'].title()}: {item['content']}" for item in messages]
    lines.append(f"User: {current}")
    lines.append("Assistant:")
    return "\n".join(lines)


@router.get("/models", response_model=ModelListResponse)
async def models(provider: OllamaProvider = Depends(get_provider)) -> ModelListResponse:
    try:
        available_models = await provider.list_models()
    except ProviderUnavailableError:
        return ModelListResponse(models=[], available=False)
    return ModelListResponse(models=available_models, available=True)


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    provider: OllamaProvider = Depends(get_provider),
    store: ConversationStore = Depends(get_store),
) -> ChatResponse:
    conversation_id = store.ensure_conversation(request.conversation_id, request.project_id)
    history = store.get_messages(conversation_id)
    store.add_message(conversation_id, "user", request.message, request.model)
    started = time.perf_counter()
    try:
        answer = await provider.generate(prompt_from_history(history, request.message), request.model)
    except ModelNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ProviderUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    store.add_message(conversation_id, "assistant", answer, request.model or provider.default_model)
    return ChatResponse(
        assistant_message=answer,
        model=request.model or provider.default_model,
        duration=time.perf_counter() - started,
        status="completed",
        conversation_id=conversation_id,
    )

@router.websocket("/chat/stream")
async def chat_stream(
    websocket: WebSocket,
    provider: OllamaProvider = Depends(get_provider),
    store: ConversationStore = Depends(get_store),
) -> None:
    await websocket.accept()

    try:
        payload = ChatRequest.model_validate(await websocket.receive_json())
        conversation_id = store.ensure_conversation(
            payload.conversation_id,
            payload.project_id,
        )
        history = store.get_messages(conversation_id)
        store.add_message(
            conversation_id,
            "user",
            payload.message,
            payload.model,
        )

        parts: list[str] = []

        async for part in provider.stream(
            prompt_from_history(history, payload.message),
            payload.model,
        ):
            parts.append(part)
            await websocket.send_json({
                "type": "token",
                "content": part,
            })

        answer = "".join(parts)

        store.add_message(
            conversation_id,
            "assistant",
            answer,
            payload.model or provider.default_model,
        )

        await websocket.send_json({
            "type": "done",
            "conversation_id": conversation_id,
            "model": payload.model or provider.default_model,
        })

    except WebSocketDisconnect:
        return
    except ModelNotFoundError as exc:
        await websocket.send_json({
            "type": "error",
            "status": 404,
            "detail": str(exc),
        })
    except ProviderUnavailableError as exc:
        await websocket.send_json({
            "type": "error",
            "status": 503,
            "detail": str(exc),
        })
    except Exception as exc:
        await websocket.send_json({
            "type": "error",
            "status": 400,
            "detail": str(exc),
        })
    finally:
        await websocket.close()
