"""
Notificaciones vía Telegram Bot API — patrón preferido y ya usado en otros
proyectos de Netxia por ser gratuito y confiable. Se usa para avisar al
equipo humano cuando hay una derivación (`transfer.requested`) o spam
bloqueado relevante.
"""
import logging
import os

import httpx

logger = logging.getLogger("netxia.notification.telegram")

TELEGRAM_API_BASE = "https://api.telegram.org"


class TelegramNotifier:
    def __init__(self, bot_token: str | None = None, chat_id: str | None = None):
        self._bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN", "")
        self._chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID", "")
        self._client = httpx.AsyncClient(timeout=10.0)

    async def close(self) -> None:
        await self._client.aclose()

    async def send(self, text: str) -> bool:
        if not self._bot_token or not self._chat_id:
            logger.warning("Telegram no configurado, se omite notificación")
            return False
        try:
            response = await self._client.post(
                f"{TELEGRAM_API_BASE}/bot{self._bot_token}/sendMessage",
                json={"chat_id": self._chat_id, "text": text, "parse_mode": "Markdown"},
            )
            response.raise_for_status()
            return True
        except httpx.HTTPError:
            logger.exception("Error enviando notificación por Telegram")
            return False
