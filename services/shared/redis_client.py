"""
Cliente Redis compartido. Implementa el esquema de memoria descrito en el
diseño:
  conversation:{tenant_id}:{user_id}:context  -> JSON del contexto activo
  conversation:{tenant_id}:{user_id}:history   -> lista (últimos N mensajes)
  session:{tenant_id}:{user_id}:state          -> estado del flujo actual

Todas las claves expiran a los `redis_context_ttl_seconds` (30 min por
defecto) de inactividad, resetando el TTL en cada escritura.
"""
import json
from typing import Any, Optional

import redis.asyncio as redis

from shared.config import settings

MAX_HISTORY_MESSAGES = 20


class RedisClient:
    def __init__(self, url: Optional[str] = None):
        self._url = url or settings.redis_url
        self._client: Optional[redis.Redis] = None

    async def connect(self) -> None:
        self._client = redis.from_url(self._url, decode_responses=True)
        await self._client.ping()

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()

    def _key(self, kind: str, tenant_id: str, user_id: str) -> str:
        prefix = "conversation" if kind in ("context", "history") else "session"
        return f"{prefix}:{tenant_id}:{user_id}:{kind if kind != 'state' else 'state'}"

    async def get_context(self, tenant_id: str, user_id: str) -> dict[str, Any]:
        raw = await self._client.get(self._key("context", tenant_id, user_id))
        return json.loads(raw) if raw else {}

    async def set_context(self, tenant_id: str, user_id: str, context: dict[str, Any]) -> None:
        key = self._key("context", tenant_id, user_id)
        await self._client.set(key, json.dumps(context), ex=settings.redis_context_ttl_seconds)

    async def append_history(self, tenant_id: str, user_id: str, role: str, content: str) -> None:
        key = self._key("history", tenant_id, user_id)
        entry = json.dumps({"role": role, "content": content})
        pipe = self._client.pipeline()
        pipe.rpush(key, entry)
        pipe.ltrim(key, -MAX_HISTORY_MESSAGES, -1)
        pipe.expire(key, settings.redis_context_ttl_seconds)
        await pipe.execute()

    async def get_history(self, tenant_id: str, user_id: str) -> list[dict[str, str]]:
        key = self._key("history", tenant_id, user_id)
        raw_items = await self._client.lrange(key, 0, -1)
        return [json.loads(item) for item in raw_items]

    async def set_state(self, tenant_id: str, user_id: str, state: str) -> None:
        key = self._key("state", tenant_id, user_id)
        await self._client.set(key, state, ex=settings.redis_context_ttl_seconds)

    async def get_state(self, tenant_id: str, user_id: str) -> Optional[str]:
        key = self._key("state", tenant_id, user_id)
        return await self._client.get(key)

    # ------------------------------------------------------------------
    # Utilidades genéricas de sets (usadas por ej. por spam-filter para
    # blacklists por tenant)
    # ------------------------------------------------------------------
    async def set_add(self, key: str, member: str) -> None:
        await self._client.sadd(key, member)

    async def set_is_member(self, key: str, member: str) -> bool:
        return bool(await self._client.sismember(key, member))

    async def incr(self, key: str) -> int:
        return await self._client.incr(key)

    async def expire(self, key: str, ttl_seconds: int) -> None:
        await self._client.expire(key, ttl_seconds)

    async def clear_conversation(self, tenant_id: str, user_id: str) -> None:
        keys = [
            self._key("context", tenant_id, user_id),
            self._key("history", tenant_id, user_id),
            self._key("state", tenant_id, user_id),
        ]
        await self._client.delete(*keys)
