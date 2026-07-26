"""
Middleware que resuelve el tenant activo a partir del subdominio o del
header `X-Tenant-ID`, y lo inyecta en `request.state.tenant_id` para que
las rutas downstream no tengan que repetir esta lógica.
"""
import logging

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("netxia.gateway.tenant")


class TenantResolutionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        tenant_id = request.headers.get("X-Tenant-ID")
        if not tenant_id:
            host = request.headers.get("host", "")
            subdomain = host.split(".")[0] if "." in host else None
            tenant_id = subdomain

        request.state.tenant_id = tenant_id
        if not tenant_id:
            logger.warning("Solicitud sin tenant resoluble: %s", request.url.path)

        return await call_next(request)
