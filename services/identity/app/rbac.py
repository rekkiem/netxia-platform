"""
Control de acceso basado en roles (RBAC). Roles definidos para el MVP:

  - platform_admin : administra todos los tenants (equipo Netxia)
  - tenant_admin    : administra la configuración de su propia empresa
  - tenant_agent    : puede ver conversaciones y tomar derivaciones
  - tenant_viewer   : solo lectura (dashboards/reportes)
"""
from enum import Enum

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.keycloak import KeycloakTokenValidator

security_scheme = HTTPBearer()
_validator = KeycloakTokenValidator()


class Role(str, Enum):
    PLATFORM_ADMIN = "platform_admin"
    TENANT_ADMIN = "tenant_admin"
    TENANT_AGENT = "tenant_agent"
    TENANT_VIEWER = "tenant_viewer"


ROLE_HIERARCHY = {
    Role.PLATFORM_ADMIN: 4,
    Role.TENANT_ADMIN: 3,
    Role.TENANT_AGENT: 2,
    Role.TENANT_VIEWER: 1,
}


async def get_current_claims(
    credentials: HTTPAuthorizationCredentials = Security(security_scheme),
) -> dict:
    try:
        return _validator.decode_token(credentials.credentials)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=401, detail="Token inválido o expirado") from exc


def require_role(minimum_role: Role):
    """Dependency factory de FastAPI: exige que el rol del usuario tenga
    al menos el nivel jerárquico de `minimum_role`."""

    async def _dependency(claims: dict = Depends(get_current_claims)) -> dict:
        roles = claims.get("realm_access", {}).get("roles", [])
        user_level = max((ROLE_HIERARCHY.get(Role(r), 0) for r in roles if r in Role.__members__.values()), default=0)
        if user_level < ROLE_HIERARCHY[minimum_role]:
            raise HTTPException(status_code=403, detail="Permisos insuficientes")
        return claims

    return _dependency
