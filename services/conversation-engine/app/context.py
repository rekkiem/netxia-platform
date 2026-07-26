"""
Gestión de contexto de conversación. Envuelve shared.redis_client con la
lógica específica del dominio (crear contexto nuevo si no existe, mergear
slots, resetear tras cierre de conversación).
"""
import logging

from app.models.context import ConversationContext
from shared.redis_client import RedisClient

logger = logging.getLogger("netxia.conversation-engine.context")


class ContextManager:
    def __init__(self, redis_client: RedisClient):
        self._redis = redis_client

    async def load_or_create(self, tenant_id: str, user_id: str, channel: str) -> ConversationContext:
        raw = await self._redis.get_context(tenant_id, user_id)
        if raw:
            return ConversationContext.model_validate(raw)
        logger.info("Nuevo contexto para tenant=%s user=%s channel=%s", tenant_id, user_id, channel)
        return ConversationContext(tenant_id=tenant_id, user_id=user_id, channel=channel)

    async def save(self, context: ConversationContext) -> None:
        await self._redis.set_context(context.tenant_id, context.user_id, context.model_dump())

    async def record_turn(self, context: ConversationContext, role: str, content: str) -> None:
        await self._redis.append_history(context.tenant_id, context.user_id, role, content)
        context.bump_turn()
        await self.save(context)

    async def get_recent_history(self, context: ConversationContext) -> list[dict[str, str]]:
        return await self._redis.get_history(context.tenant_id, context.user_id)

    async def close_conversation(self, context: ConversationContext) -> None:
        await self._redis.clear_conversation(context.tenant_id, context.user_id)
