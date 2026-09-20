# Route is lifecycle plumbing only — auth, accept, dispatch loop, disconnect.
# Per-turn orchestration lives in app.services.agent_session.AgentSession.
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.deps import CurrentUserWS
from app.core.config import settings
from app.schemas.base import AgentModelsResponse
from app.services.agent import AgentConnectionManager
from app.services.agent_session import AgentSession

logger = logging.getLogger(__name__)

router = APIRouter()

manager = AgentConnectionManager()


import httpx
from app.agents.openai_compatible_client import normalize_endpoint_url


@router.get("/agent/models", response_model=AgentModelsResponse)
async def list_models() -> dict[str, Any]:
    """Return available LLM models and auto-discover locally running Ollama models."""
    ollama_running = False
    ollama_models: list[str] = []
    # Test Ollama through normalized endpoint (handles Docker host mapping)
    candidate_urls = [
        normalize_endpoint_url("http://localhost:11434"),
        "http://localhost:11434/v1",
        "http://host.docker.internal:11434/v1",
    ]
    for url in dict.fromkeys(candidate_urls):
        base = url.rstrip("/")
        models_endpoint = base if base.endswith("/models") else f"{base}/models"
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get(models_endpoint)
                if res.status_code == 200:
                    data = res.json()
                    ollama_running = True
                    # OpenAI /v1/models returns {"data": [{"id": ...}]}
                    if "data" in data and isinstance(data["data"], list):
                        ollama_models = [m["id"] for m in data["data"] if "id" in m]
                    elif "models" in data and isinstance(data["models"], list):
                        ollama_models = [m.get("name") for m in data["models"] if m.get("name")]
                    if ollama_models:
                        break
        except Exception:
            continue

    return {
        "default": settings.AI_MODEL,
        "models": settings.AI_AVAILABLE_MODELS,
        "ollama_running": ollama_running,
        "ollama_models": ollama_models,
        "ollama_base_url": "http://localhost:11434/v1",
    }


@router.websocket("/ws/agent")
async def agent_websocket(
    websocket: WebSocket,
    user: CurrentUserWS,
) -> None:
    if user is None:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await manager.connect(websocket)
    session = AgentSession(
        websocket,
        user,
    )

    try:
        while True:
            try:
                data = await websocket.receive_json()
            except WebSocketDisconnect:
                break
            await session.handle_frame(data)
    finally:
        await session.shutdown()
        manager.disconnect(websocket)
