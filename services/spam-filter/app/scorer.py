"""
Scoring dinámico de spam. Combina las reglas heurísticas de `rules.py`
con la blacklist de `blacklist.py` para producir un score final 0.0-1.0 y
una acción recomendada: "blocked" (>=0.85), "flagged" (>=0.5) o "allowed".

Criterio de éxito del MVP: >95% de precisión con <1% de falsos positivos.
Estas reglas son deliberadamente conservadoras (pesos bajos salvo en
blacklist/prefijo conocido) para minimizar el riesgo de bloquear clientes
legítimos; se espera calibrar los pesos con datos reales de producción.
"""
import logging
from datetime import datetime, timezone

from app.blacklist import is_tenant_blacklisted, matches_known_spam_prefix
from app.rules import rule_no_caller_id, rule_outside_business_hours, rule_repeat_calls
from shared.redis_client import RedisClient

logger = logging.getLogger("netxia.spam-filter.scorer")

BLOCK_THRESHOLD = 0.85
FLAG_THRESHOLD = 0.5


async def score_call(
    redis_client: RedisClient,
    tenant_id: str,
    phone_number: str,
    has_caller_id: bool,
    recent_call_count: int,
) -> tuple[float, str]:
    if await is_tenant_blacklisted(redis_client, tenant_id, phone_number):
        return 1.0, "blocked"

    score = 0.0
    score += rule_no_caller_id(has_caller_id) if matches_known_spam_prefix(phone_number) else 0.0
    score = max(score, 0.9 if matches_known_spam_prefix(phone_number) else 0.0)
    score += rule_outside_business_hours(datetime.now(timezone.utc))
    score += rule_repeat_calls(recent_call_count)
    score = min(score, 1.0)

    if score >= BLOCK_THRESHOLD:
        action = "blocked"
    elif score >= FLAG_THRESHOLD:
        action = "flagged"
    else:
        action = "allowed"

    logger.debug("Score spam para %s: %.2f -> %s", phone_number, score, action)
    return round(score, 2), action


async def register_call_attempt(redis_client: RedisClient, phone_number: str) -> int:
    """Incrementa un contador con TTL para detectar llamadas repetidas en
    ventana corta (marcador automático)."""
    from app.rules import REPEAT_CALL_WINDOW_SECONDS

    key = f"spam:call_count:{phone_number}"
    count = await redis_client.incr(key)
    if count == 1:
        await redis_client.expire(key, REPEAT_CALL_WINDOW_SECONDS)
    return count
