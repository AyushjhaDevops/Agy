from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.agents import router as agents_router
from app.api.chat import router as chat_router
from app.api.projects import router as projects_router
from app.api.system import router as system_router
from app.api.tasks import router as tasks_router
from app.api.terminal import router as terminal_router
from app.core.config import get_settings

settings = get_settings()
app = FastAPI(title=settings.app_name, description="Local-first LocalForge AI API.", version="0.6.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_credentials=True, allow_methods=["GET", "POST"], allow_headers=["*"])
app.include_router(system_router)
app.include_router(chat_router)
app.include_router(projects_router)
app.include_router(tasks_router)
app.include_router(agents_router)
app.include_router(terminal_router)
