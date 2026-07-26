import logging

import httpx

from app.adapters.base import CRMAdapter, CRMAdapterError

logger = logging.getLogger("netxia.crm-service.suitecrm")


class SuiteCRMAdapter(CRMAdapter):
    """Adaptador para SuiteCRM vía su API v4_1 (OAuth2 client_credentials)."""

    def __init__(self, base_url: str = "", access_token: str = ""):
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {access_token}"}, timeout=10.0
        )

    async def upsert_contact(self, tenant_id: str, phone_number: str, name: str | None) -> str:
        try:
            response = await self._client.post(
                f"{self._base_url}/Api/V8/module",
                json={
                    "data": {
                        "type": "Contacts",
                        "attributes": {"phone_mobile": phone_number, "last_name": name or phone_number},
                    }
                },
            )
            response.raise_for_status()
            return response.json()["data"]["id"]
        except httpx.HTTPError as exc:
            raise CRMAdapterError(f"SuiteCRM upsert_contact falló: {exc}") from exc

    async def log_conversation(self, tenant_id: str, contact_id: str, summary: str, channel: str) -> None:
        try:
            response = await self._client.post(
                f"{self._base_url}/Api/V8/module",
                json={
                    "data": {
                        "type": "Notes",
                        "attributes": {"name": f"Conversación {channel}", "description": summary},
                        "relationships": {"parent": {"data": {"type": "Contacts", "id": contact_id}}},
                    }
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise CRMAdapterError(f"SuiteCRM log_conversation falló: {exc}") from exc

    async def is_healthy(self) -> bool:
        try:
            response = await self._client.get(f"{self._base_url}/Api/V8/meta")
            return response.status_code == 200
        except httpx.HTTPError:
            return False
