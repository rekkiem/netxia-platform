import logging

from fastapi import Depends, FastAPI

from app.keycloak import KeycloakTokenValidator
from app.rbac import Role, get_current_claims, require_role
from shared.config import settings

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("netxia.identity")

app = FastAPI(title="Netxia Identity Service", version="1.0.0")
validator = KeycloakTokenValidator()


@app.get("/v1/me")
async def me(claims: dict = Depends(get_current_claims)) -> dict:
    return {"sub": claims.get("sub"), "roles": claims.get("realm_access", {}).get("roles", [])}


@app.get("/v1/admin/ping")
async def admin_ping(_: dict = Depends(require_role(Role.TENANT_ADMIN))) -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health")
async def health() -> dict[str, str | bool]:
    reachable = await validator.is_reachable()
    return {"status": "ok" if reachable else "degraded", "keycloak_reachable": reachable}
