"""
Punto de entrada del Voice Service.

Levanta:
1. Un servidor TCP AudioSocket (puerto 8090) que Asterisk usa para
   streamear audio bidireccional de cada llamada.
2. Un consumer de RabbitMQ para `voice.outgoing` (respuesta ya generada
   por el conversation-engine) que sintetiza el audio con Piper y lo
   reenvía al socket de la llamada correspondiente.
3. Un healthcheck HTTP simple para Docker/Traefik.
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI

from app.audiosocket import AudioSocketMessage, CallSession, FrameType, read_message, write_message
from app.tts import synthesize_speech
from shared.config import settings
from shared.events import EventType, VoiceEvent
from shared.rabbitmq import RabbitMQClient

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("netxia.voice-service")

AUDIOSOCKET_PORT = 8090
DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"

rabbitmq = RabbitMQClient()
_active_writers: dict[str, asyncio.StreamWriter] = {}


async def _on_utterance(call_id: str, transcript: str) -> None:
    event = VoiceEvent(
        event_type=EventType.VOICE_INCOMING,
        tenant_id=DEFAULT_TENANT_ID,  # en multi-tenant real, se resuelve por DID marcado
        call_id=call_id,
        payload={"transcript": transcript},
    )
    await rabbitmq.publish(event)


async def _handle_outgoing_voice(event: VoiceEvent) -> None:
    call_id = event.payload.get("call_id")
    text = event.payload.get("response_text")
    writer = _active_writers.get(call_id)
    if not writer or not text:
        logger.warning("No hay socket activo para call_id=%s, se descarta respuesta", call_id)
        return
    try:
        audio_bytes = await synthesize_speech(text)
        write_message(writer, FrameType.AUDIO, audio_bytes)
        await writer.drain()
    except Exception:  # noqa: BLE001
        logger.exception("Error sintetizando/enviando audio para call_id=%s", call_id)


async def _handle_connection(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    call_id = str(uuid4())
    _active_writers[call_id] = writer
    session = CallSession(call_id, _on_utterance)
    logger.info("Nueva conexión AudioSocket, call_id=%s", call_id)
    try:
        while True:
            message: AudioSocketMessage | None = await read_message(reader)
            if message is None or message.frame_type == FrameType.HANGUP:
                break
            if message.frame_type == FrameType.AUDIO:
                await session.feed(message.payload)
    except (asyncio.IncompleteReadError, ConnectionResetError):
        logger.info("Conexión AudioSocket cerrada por el peer, call_id=%s", call_id)
    finally:
        _active_writers.pop(call_id, None)
        writer.close()


async def _run_audiosocket_server() -> None:
    server = await asyncio.start_server(_handle_connection, host="0.0.0.0", port=AUDIOSOCKET_PORT)
    logger.info("Servidor AudioSocket escuchando en puerto %s", AUDIOSOCKET_PORT)
    async with server:
        await server.serve_forever()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await rabbitmq.connect()
    await rabbitmq.subscribe(
        queue_name="voice-service.outgoing",
        routing_keys=[EventType.VOICE_OUTGOING.value],
        event_cls=VoiceEvent,
        handler=_handle_outgoing_voice,
    )
    server_task = asyncio.create_task(_run_audiosocket_server())
    logger.info("Voice Service iniciado")
    yield
    server_task.cancel()
    await rabbitmq.close()


app = FastAPI(title="Netxia Voice Service", version="1.0.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "voice-service"}
