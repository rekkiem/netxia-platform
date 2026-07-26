"""
Genera un reporte de texto plano (para enviar por Telegram/email vía
notification-service) resumiendo las métricas clave de un tenant en un
período dado. Post-MVP: reemplazar por reportes en PDF/Grafana embebido.
"""
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.metrics import average_resolution_seconds, conversation_volume, escalation_rate


async def build_daily_report(session: AsyncSession, tenant_id: UUID, since: datetime) -> str:
    volume = await conversation_volume(session, tenant_id, since)
    escalation = await escalation_rate(session, tenant_id, since)
    avg_resolution = await average_resolution_seconds(session, tenant_id, since)

    total_conversations = sum(volume.values())
    volume_lines = "\n".join(f"  - {channel}: {count}" for channel, count in volume.items()) or "  - Sin datos"
    resolution_text = f"{avg_resolution:.0f}s" if avg_resolution is not None else "N/D"

    return (
        f"Reporte diario Netxia — {since.strftime('%Y-%m-%d')}\n"
        f"Conversaciones totales: {total_conversations}\n"
        f"Por canal:\n{volume_lines}\n"
        f"Tasa de derivación a humano: {escalation * 100:.1f}%\n"
        f"Tiempo promedio de resolución: {resolution_text}"
    )
