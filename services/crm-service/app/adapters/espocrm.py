import logging

import httpx

from app.adapters.base import CRMAdapter, CRMAdapterError

logger = logging.getLogger("netxia.crm-service.espocrm")


class EspoCRMAdapter(CRMAdapter):
    """Adaptador para EspoCRM vía su API REST estándar (X-Api-Key)."""

    def __init__(self, base_url: str = "", api_key: str = ""):
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(headers={"X-Api-Key": api_key}, timeout=10.0)

    async def upsert_contact(self, tenant_id: str, phone_number: str, name: str | None) -> str:
        try:
            response = await self._client.post(
                f"{self._base_url}/api/v1/Contact",
                json={"phoneNumber": phone_number, "name": name or phone_number},
            )
            response.raise_for_status()
            return response.json()["id"]
        except httpx.HTTPError as exc:
            raise CRMAdapterError(f"EspoCRM upsert_contact falló: {exc}") from exc

    async def log_conversation(self, tenant_id: str, contact_id: str, summary: str, channel: str) -> None:
        try:
            response = await self._client.post(
                f"{self._base_url}/api/v1/Note",
                json={"parentId": contact_id, "parentType": "Contact", "post": summary, "type": channel},
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise CRMAdapterError(f"EspoCRM log_conversation falló: {exc}") from exc

    async def is_healthy(self) -> bool:
        try:
            response = await self._client.get(f"{self._base_url}/api/v1/App/user")
            return response.status_code == 200
        except httpx.HTTPError:
            return False
