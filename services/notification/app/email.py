"""
Notificaciones por email vía Web3Forms (API HTTP), el mismo patrón usado
en netxia.cl cuando SMTP está bloqueado a nivel de sistema operativo en el
hosting. Canal secundario a Telegram, usado para resúmenes diarios/reportes.
"""
import logging
import os

import httpx

logger = logging.getLogger("netxia.notification.email")

WEB3FORMS_ENDPOINT = "https://api.web3forms.com/submit"


class EmailNotifier:
    def __init__(self, access_key: str | None = None, to_email: str | None = None):
        self._access_key = access_key or os.getenv("WEB3FORMS_ACCESS_KEY", "")
        self._to_email = to_email or os.getenv("NOTIFICATION_EMAIL", "")
        self._client = httpx.AsyncClient(timeout=10.0)

    async def close(self) -> None:
        await self._client.aclose()

    async def send(self, subject: str, message: str) -> bool:
        if not self._access_key or not self._to_email:
            logger.warning("Web3Forms no configurado, se omite notificación por email")
            return False
        try:
            response = await self._client.post(
                WEB3FORMS_ENDPOINT,
                data={
                    "access_key": self._access_key,
                    "subject": subject,
                    "email": self._to_email,
                    "message": message,
                },
            )
            response.raise_for_status()
            return response.json().get("success", False)
        except httpx.HTTPError:
            logger.exception("Error enviando notificación por email")
            return False
