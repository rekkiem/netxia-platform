"""
Cliente para Evolution API (bridge open source de WhatsApp vía Baileys).
Cada tenant tiene su propia "instancia" en Evolution API, identificada por
`instance_id`, lo que permite el aislamiento multi-tenant a nivel de
número de WhatsApp.
"""
import logging

import httpx

from shared.config import settings

logger = logging.getLogger("netxia.whatsapp-service.client")

REQUEST_TIMEOUT_SECONDS = 10.0


class EvolutionAPIClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self._base_url = (base_url or settings.evolution_api_url).rstrip("/")
        self._api_key = api_key or settings.evolution_api_key
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=REQUEST_TIMEOUT_SECONDS,
            headers={"apikey": self._api_key},
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def send_text_message(self, instance_id: str, to_number: str, text: str) -> bool:
        try:
            response = await self._client.post(
                f"/message/sendText/{instance_id}",
                json={"number": to_number, "text": text},
            )
            response.raise_for_status()
            return True
        except httpx.HTTPError:
            logger.exception("Error enviando mensaje WhatsApp a %s vía instancia %s", to_number, instance_id)
            return False

    async def get_instance_status(self, instance_id: str) -> str:
        try:
            response = await self._client.get(f"/instance/connectionState/{instance_id}")
            response.raise_for_status()
            return response.json().get("state", "unknown")
        except httpx.HTTPError:
            logger.exception("Error consultando estado de instancia %s", instance_id)
            return "unreachable"
