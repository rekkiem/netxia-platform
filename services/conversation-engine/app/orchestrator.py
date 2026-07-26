"""
Orquestador principal de conversaciones.

Responsable de:
- Consumir VoiceEvent / WhatsAppEvent desde RabbitMQ
- Gestionar el contexto de la conversación (Redis)
- Recuperar contexto adicional vía RAG (pgvector)
- Invocar al LLM Service (router de modelos) por HTTP
- Evaluar sentimiento y decidir si escalar a un humano
- Persistir la conversación en PostgreSQL
- Publicar la respuesta de vuelta (voice.outgoing / whatsapp.outgoing)

Este módulo NO habla directamente con Asterisk, Whisper, Piper ni
Evolution API: eso es responsabilidad de voice-service y whatsapp-service,
respectivamente. El orquestador solo trabaja con eventos y texto.
"""
import logging
from uuid import UUID, uuid4

import httpx
from sqlalchemy import select

from app.context import ContextManager
from app.prompts import build_messages
from app.sentiment import analyze_sentiment
from app.transfer import escalate_to_human, should_escalate
from shared.database import session_scope
from shared.events import BaseEvent, EventType, VoiceEvent, WhatsAppEvent
from shared.rabbitmq import RabbitMQClient
from shared.redis_client import RedisClient

logger = logging.getLogger("netxia.conversation-engine.orchestrator")

LLM_SERVICE_URL = "http://llm-service:8000/v1/generate"
LLM_TIMEOUT_SECONDS = 15.0


class ConversationOrchestrator:
    def __init__(self, rabbitmq: RabbitMQClient, redis: RedisClient):
        self.rabbitmq = rabbitmq
        self.redis = redis
        self.context_manager = ContextManager(redis)
        self._http_client = httpx.AsyncClient(timeout=LLM_TIMEOUT_SECONDS)

    async def start(self) -> None:
        """Registra los consumidores de eventos. Se llama una vez al boot."""
        await self.rabbitmq.subscribe(
            queue_name="conversation-engine.voice",
            routing_keys=[EventType.VOICE_INCOMING.value],
            event_cls=VoiceEvent,
            handler=self.handle_voice_event,
        )
        await self.rabbitmq.subscribe(
            queue_name="conversation-engine.whatsapp",
            routing_keys=[EventType.WHATSAPP_INCOMING.value],
            event_cls=WhatsAppEvent,
            handler=self.handle_whatsapp_event,
        )
        logger.info("Conversation Engine escuchando eventos de voz y WhatsApp")

    async def shutdown(self) -> None:
        await self._http_client.aclose()

    # ------------------------------------------------------------------
    # Manejo de canal de voz
    # ------------------------------------------------------------------
    async def handle_voice_event(self, event: VoiceEvent) -> None:
        transcript = event.payload.get("transcript")
        if not transcript:
            logger.warning("VoiceEvent sin transcripción, se ignora: %s", event.event_id)
            return

        response_text = await self._process_turn(
            tenant_id=event.tenant_id,
            user_id=event.caller_number or "desconocido",
            channel="voice",
            user_message=transcript,
        )

        outgoing = VoiceEvent(
            event_type=EventType.VOICE_OUTGOING,
            tenant_id=event.tenant_id,
            correlation_id=event.event_id,
            call_id=event.call_id,
            caller_number=event.caller_number,
            payload={"response_text": response_text, "call_id": event.call_id},
        )
        await self.rabbitmq.publish(outgoing)

    # ------------------------------------------------------------------
    # Manejo de canal WhatsApp
    # ------------------------------------------------------------------
    async def handle_whatsapp_event(self, event: WhatsAppEvent) -> None:
        message_text = event.payload.get("text")
        if not message_text:
            logger.warning("WhatsAppEvent sin texto, se ignora: %s", event.event_id)
            return

        response_text = await self._process_turn(
            tenant_id=event.tenant_id,
            user_id=event.from_number or "desconocido",
            channel="whatsapp",
            user_message=message_text,
        )

        outgoing = WhatsAppEvent(
            event_type=EventType.WHATSAPP_OUTGOING,
            tenant_id=event.tenant_id,
            correlation_id=event.event_id,
            from_number=event.from_number,
            instance_id=event.instance_id,
            payload={"text": response_text, "to": event.from_number},
        )
        await self.rabbitmq.publish(outgoing)

    # ------------------------------------------------------------------
    # Lógica compartida entre canales
    # ------------------------------------------------------------------
    async def _process_turn(self, tenant_id: UUID, user_id: str, channel: str, user_message: str) -> str:
        context = await self.context_manager.load_or_create(str(tenant_id), user_id, channel)
        if not context.conversation_id:
            context.conversation_id = str(uuid4())
            await self._persist_conversation_start(tenant_id, user_id, channel, context.conversation_id)

        history = await self.context_manager.get_recent_history(context)

        # Sentimiento y posible escalamiento ANTES de llamar al LLM, para no
        # gastar cómputo en generar una respuesta si el cliente ya pidió humano.
        context.sentiment_score = analyze_sentiment(user_message)
        must_escalate, reason = should_escalate(context, user_message)
        if must_escalate:
            await escalate_to_human(self.rabbitmq, context, reason)
            await self.context_manager.save(context)
            return (
                "Entiendo. Te voy a derivar con una persona de nuestro equipo que te "
                "podrá ayudar mejor. Un momento, por favor."
            )

        rag_snippets = await self._retrieve_rag_snippets(tenant_id, user_message)
        model_choice = self._select_model(user_message, context.turn_count)

        messages = build_messages(
            tenant_name="Netxia",
            channel=channel,
            history=history,
            user_message=user_message,
            rag_snippets=rag_snippets,
        )

        response_text = await self._call_llm(model_choice, messages)

        context.last_model_used = model_choice
        await self.context_manager.record_turn(context, "user", user_message)
        await self.context_manager.record_turn(context, "assistant", response_text)
        await self._persist_messages(context.conversation_id, user_message, response_text)

        return response_text

    async def _retrieve_rag_snippets(self, tenant_id: UUID, query: str) -> list[str]:
        try:
            from app.rag import retrieve_relevant_snippets

            async with session_scope() as session:
                return await retrieve_relevant_snippets(session, tenant_id, query)
        except Exception:  # noqa: BLE001
            # Degradación elegante: si RAG falla (embeddings no cargados,
            # DB caída, etc.), seguimos sin contexto extra en vez de romper
            # la conversación completa.
            logger.exception("RAG falló, continuando sin snippets adicionales")
            return []

    @staticmethod
    def _select_model(user_message: str, turn_count: int) -> str:
        """Router de modelos simple basado en heurísticas de longitud/turno.
        La lógica fina de qué modelo Ollama usar vive en llm-service; aquí
        solo elegimos la 'categoría' (fast/default/reasoning)."""
        word_count = len(user_message.split())
        if turn_count == 0 and word_count <= 6:
            return "fast"
        if word_count > 40 or turn_count >= 5:
            return "reasoning"
        return "default"

    async def _call_llm(self, model_choice: str, messages: list[dict[str, str]]) -> str:
        try:
            response = await self._http_client.post(
                LLM_SERVICE_URL,
                json={"model_choice": model_choice, "messages": messages},
            )
            response.raise_for_status()
            return response.json()["text"]
        except httpx.HTTPError:
            logger.exception("Error llamando a llm-service")
            return (
                "Disculpa, estoy teniendo problemas técnicos en este momento. "
                "¿Podrías repetir tu consulta o prefieres que te contacte un ejecutivo?"
            )

    async def _persist_conversation_start(
        self, tenant_id: UUID, user_id: str, channel: str, conversation_id: str
    ) -> None:
        async with session_scope() as session:
            await session.execute(
                select(1)  # placeholder de verificación de conexión antes del insert real
            )
            from sqlalchemy import text as sql_text

            await session.execute(
                sql_text(
                    """
                    INSERT INTO conversations (id, tenant_id, user_id, channel, status, started_at)
                    VALUES (:id, :tenant_id, :user_id, :channel, 'active', now())
                    """
                ),
                {
                    "id": conversation_id,
                    "tenant_id": str(tenant_id),
                    "user_id": user_id,
                    "channel": channel,
                },
            )

    async def _persist_messages(self, conversation_id: str, user_message: str, response_text: str) -> None:
        async with session_scope() as session:
            from sqlalchemy import text as sql_text

            await session.execute(
                sql_text(
                    """
                    INSERT INTO messages (id, conversation_id, role, content, created_at)
                    VALUES (gen_random_uuid(), :conversation_id, 'user', :content, now())
                    """
                ),
                {"conversation_id": conversation_id, "content": user_message},
            )
            await session.execute(
                sql_text(
                    """
                    INSERT INTO messages (id, conversation_id, role, content, created_at)
                    VALUES (gen_random_uuid(), :conversation_id, 'assistant', :content, now())
                    """
                ),
                {"conversation_id": conversation_id, "content": response_text},
            )
