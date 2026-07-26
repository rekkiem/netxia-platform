import logging

import httpx

from app.adapters.base import CRMAdapter, CRMAdapterError

logger = logging.getLogger("netxia.crm-service.odoo")


class OdooAdapter(CRMAdapter):
    """Adaptador para Odoo vía JSON-RPC (external API)."""

    def __init__(self, base_url: str = "", db: str = "", api_key: str = ""):
        self._base_url = base_url.rstrip("/")
        self._db = db
        self._api_key = api_key
        self._client = httpx.AsyncClient(timeout=10.0)

    async def _call(self, model: str, method: str, args: list) -> dict:
        response = await self._client.post(
            f"{self._base_url}/jsonrpc",
            json={
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "service": "object",
                    "method": "execute_kw",
                    "args": [self._db, 1, self._api_key, model, method, args],
                },
            },
        )
        response.raise_for_status()
        return response.json()

    async def upsert_contact(self, tenant_id: str, phone_number: str, name: str | None) -> str:
        try:
            result = await self._call(
                "res.partner", "create", [{"phone": phone_number, "name": name or phone_number}]
            )
            return str(result["result"])
        except httpx.HTTPError as exc:
            raise CRMAdapterError(f"Odoo upsert_contact falló: {exc}") from exc

    async def log_conversation(self, tenant_id: str, contact_id: str, summary: str, channel: str) -> None:
        try:
            await self._call(
                "mail.message",
                "create",
                [{"body": summary, "res_id": int(contact_id), "model": "res.partner", "subtype": channel}],
            )
        except httpx.HTTPError as exc:
            raise CRMAdapterError(f"Odoo log_conversation falló: {exc}") from exc

    async def is_healthy(self) -> bool:
        try:
            response = await self._client.get(f"{self._base_url}/web/webclient/version_info")
            return response.status_code == 200
        except httpx.HTTPError:
            return False
