"""
Validación de tokens JWT emitidos por Keycloak (OIDC). El resto de los
servicios no hablan con Keycloak directamente: usan este módulo como
dependency de FastAPI para proteger sus rutas.
"""
import logging

import httpx
import jwt
from jwt import PyJWKClient

from shared.config import settings

logger = logging.getLogger("netxia.identity.keycloak")

KEYCLOAK_REALM = "netxia"
KEYCLOAK_BASE_URL = "http://keycloak:8080"


class KeycloakTokenValidator:
    def __init__(self, base_url: str = KEYCLOAK_BASE_URL, realm: str = KEYCLOAK_REALM):
        self._issuer = f"{base_url}/realms/{realm}"
        jwks_url = f"{self._issuer}/protocol/openid-connect/certs"
        self._jwk_client = PyJWKClient(jwks_url)

    def decode_token(self, token: str) -> dict:
        signing_key = self._jwk_client.get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=self._issuer,
            options={"verify_aud": False},
        )

    async def is_reachable(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self._issuer}/.well-known/openid-configuration")
                return response.status_code == 200
        except httpx.HTTPError:
            return False
