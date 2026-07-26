"""
Listas negras estáticas: prefijos de numeración conocidos como spam/robocall
en Chile, y una tabla de números explícitamente bloqueados por tenant
(persistida en Redis para poder actualizarla en caliente sin redeploy).
"""
import re

from shared.redis_client import RedisClient

# Prefijos frecuentemente asociados a campañas de robocall/telemarketing
# no solicitado en Chile. Lista base, ampliable vía configuración de tenant.
KNOWN_SPAM_PREFIXES = [
    r"^\+5692",   # rangos de VoIP masivo genérico
    r"^\+56800",  # números 800 usados para campañas salientes masivas
]

_COMPILED_PATTERNS = [re.compile(p) for p in KNOWN_SPAM_PREFIXES]


def matches_known_spam_prefix(phone_number: str) -> bool:
    return any(pattern.match(phone_number) for pattern in _COMPILED_PATTERNS)


async def is_tenant_blacklisted(redis_client: RedisClient, tenant_id: str, phone_number: str) -> bool:
    key = f"blacklist:{tenant_id}"
    return await redis_client.set_is_member(key, phone_number)


async def add_to_tenant_blacklist(redis_client: RedisClient, tenant_id: str, phone_number: str) -> None:
    key = f"blacklist:{tenant_id}"
    await redis_client.set_add(key, phone_number)
