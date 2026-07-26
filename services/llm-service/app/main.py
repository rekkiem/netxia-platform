import logging
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.ollama_client import OllamaClient
from app.router import ModelRouter
from shared.config import settings

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("netxia.llm-service")

ollama_client = OllamaClient()
model_router = ModelRouter(ollama_client)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("LLM Service iniciado. Ollama host: %s", settings.ollama_host)
    yield
    await ollama_client.close()


app = FastAPI(title="Netxia LLM Service", version="1.0.0", lifespan=lifespan)


class GenerateRequest(BaseModel):
    model_choice: Literal["fast", "default", "reasoning"] = "default"
    messages: list[dict[str, str]]


class GenerateResponse(BaseModel):
    text: str
    model_used: str


@app.post("/v1/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest) -> GenerateResponse:
    if not request.messages:
        raise HTTPException(status_code=422, detail="messages no puede estar vacío")
    try:
        text = await model_router.generate(request.model_choice, request.messages)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return GenerateResponse(text=text, model_used=model_router.resolve_model_name(request.model_choice))


@app.get("/health")
async def health() -> dict[str, str | bool]:
    healthy = await ollama_client.is_healthy()
    return {"status": "ok" if healthy else "degraded", "ollama_reachable": healthy}
