"""
Cliente RabbitMQ compartido, construido sobre aio-pika.

Todos los eventos se publican en un único exchange topic `netxia.events`.
Cada servicio declara su propia cola y la bindea a los routing keys
(event types) que le interesan. Esto permite agregar nuevos consumidores
sin tocar a los publishers (desacoplamiento total, tal como exige el
diseño de arquitectura).
"""
import asyncio
import logging
from typing import Awaitable, Callable, Optional

import aio_pika
from aio_pika import ExchangeType
from aio_pika.abc import AbstractIncomingMessage

from shared.config import settings
from shared.events import BaseEvent

logger = logging.getLogger("netxia.rabbitmq")

EXCHANGE_NAME = "netxia.events"
MessageHandler = Callable[[BaseEvent], Awaitable[None]]


class RabbitMQClient:
    def __init__(self, url: Optional[str] = None):
        self._url = url or settings.rabbitmq_url
        self._connection: Optional[aio_pika.RobustConnection] = None
        self._channel: Optional[aio_pika.abc.AbstractChannel] = None
        self._exchange: Optional[aio_pika.abc.AbstractExchange] = None

    async def connect(self, retries: int = 5, delay_seconds: float = 3.0) -> None:
        last_error: Optional[Exception] = None
        for attempt in range(1, retries + 1):
            try:
                self._connection = await aio_pika.connect_robust(self._url)
                self._channel = await self._connection.channel()
                await self._channel.set_qos(prefetch_count=10)
                self._exchange = await self._channel.declare_exchange(
                    EXCHANGE_NAME, ExchangeType.TOPIC, durable=True
                )
                logger.info("Conectado a RabbitMQ (intento %s)", attempt)
                return
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.warning("Fallo conexión RabbitMQ intento %s: %s", attempt, exc)
                await asyncio.sleep(delay_seconds)
        raise ConnectionError(f"No se pudo conectar a RabbitMQ tras {retries} intentos") from last_error

    async def close(self) -> None:
        if self._connection:
            await self._connection.close()

    async def publish(self, event: BaseEvent) -> None:
        if self._exchange is None:
            raise RuntimeError("RabbitMQClient no está conectado. Llama a connect() primero.")
        message = aio_pika.Message(
            body=event.model_dump_json().encode("utf-8"),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )
        await self._exchange.publish(message, routing_key=event.event_type.value)
        logger.debug("Evento publicado: %s (%s)", event.event_type.value, event.event_id)

    async def subscribe(
        self,
        queue_name: str,
        routing_keys: list[str],
        event_cls: type[BaseEvent],
        handler: MessageHandler,
    ) -> None:
        """Declara una cola durable, la bindea a los routing keys dados y
        consume mensajes indefinidamente, ack-eando solo si `handler` no
        lanza excepción (para permitir reintentos)."""
        if self._channel is None or self._exchange is None:
            raise RuntimeError("RabbitMQClient no está conectado. Llama a connect() primero.")

        queue = await self._channel.declare_queue(queue_name, durable=True)
        for key in routing_keys:
            await queue.bind(self._exchange, routing_key=key)

        async def _on_message(message: AbstractIncomingMessage) -> None:
            async with message.process(requeue=True, ignore_processed=True):
                try:
                    event = event_cls.model_validate_json(message.body)
                    await handler(event)
                except Exception:  # noqa: BLE001
                    logger.exception("Error procesando mensaje de %s", queue_name)
                    raise

        await queue.consume(_on_message)
        logger.info("Suscrito a cola '%s' con routing keys %s", queue_name, routing_keys)
