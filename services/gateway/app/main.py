import logging

from fastapi import FastAPI

from app.middleware.tenant import TenantResolutionMiddleware
from app.routes import conversations, tenants
from shared.config import settings

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("netxia.gateway")

app = FastAPI(
    title="Netxia Conversational Platform - API Gateway",
    version="1.0.0",
    description="Punto de entrada único para administración y consulta del NCP.",
)
app.add_middleware(TenantResolutionMiddleware)
app.include_router(tenants.router)
app.include_router(conversations.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "gateway"}
