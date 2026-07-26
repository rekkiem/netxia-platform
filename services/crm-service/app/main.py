import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.adapters.base import CRMAdapterError, get_adapter
from shared.config import settings
from shared.events import BaseEvent, EventType
from shared.rabbitmq import RabbitMQClient

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("netxia.crm-service")

rabbitmq = RabbitMQClient()


async def _handle_crm_sync(event: BaseEvent) -> None:
    crm_type = event.payload.get("crm_type")
    if not crm_type:
        logger.warning("crm.sync sin crm_type, se ignora: %s", event.event_id)
        return
    try:
        adapter = get_adapter(crm_type)
        contact_id = await adapter.upsert_contact(
            str(event.tenant_id), event.payload["phone_number"], event.payload.get("name")
        )
        await adapter.log_conversation(
            str(event.tenant_id), contact_id, event.payload.get("summary", ""), event.payload.get("channel", "")
        )
    except CRMAdapterError:
        logger.exception("Fallo de sincronización con CRM para tenant %s", event.tenant_id)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await rabbitmq.connect()
    await rabbitmq.subscribe(
        queue_name="crm-service.sync",
        routing_keys=[EventType.CRM_SYNC.value],
        event_cls=BaseEvent,
        handler=_handle_crm_sync,
    )
    logger.info("CRM Service iniciado")
    yield
    await rabbitmq.close()


app = FastAPI(title="Netxia CRM Service", version="1.0.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "crm-service"}
