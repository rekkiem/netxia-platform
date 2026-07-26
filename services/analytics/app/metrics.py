"""
Cálculo de métricas de negocio a partir de PostgreSQL: volumen de
conversaciones, tasa de derivación a humano, tiempo promedio de
resolución, y distribución de uso de modelos LLM (para monitorear costo
computacional del router).
"""
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def conversation_volume(session: AsyncSession, tenant_id: UUID, since: datetime) -> dict:
    result = await session.execute(
        text(
            """
            SELECT channel, count(*) AS total
            FROM conversations
            WHERE tenant_id = :tenant_id AND started_at >= :since
            GROUP BY channel
            """
        ),
        {"tenant_id": str(tenant_id), "since": since},
    )
    return {row.channel: row.total for row in result.fetchall()}


async def escalation_rate(session: AsyncSession, tenant_id: UUID, since: datetime) -> float:
    result = await session.execute(
        text(
            """
            SELECT
                count(*) FILTER (WHERE status = 'escalated') AS escalated,
                count(*) AS total
            FROM conversations
            WHERE tenant_id = :tenant_id AND started_at >= :since
            """
        ),
        {"tenant_id": str(tenant_id), "since": since},
    )
    row = result.fetchone()
    if not row or row.total == 0:
        return 0.0
    return round(row.escalated / row.total, 4)


async def average_resolution_seconds(session: AsyncSession, tenant_id: UUID, since: datetime) -> float | None:
    result = await session.execute(
        text(
            """
            SELECT avg(extract(epoch FROM (ended_at - started_at))) AS avg_seconds
            FROM conversations
            WHERE tenant_id = :tenant_id AND started_at >= :since AND ended_at IS NOT NULL
            """
        ),
        {"tenant_id": str(tenant_id), "since": since},
    )
    row = result.fetchone()
    return round(row.avg_seconds, 1) if row and row.avg_seconds is not None else None
