"""
Endpoints de consulta para el dashboard/administración: listar
conversaciones y mensajes de un tenant. Toda escritura de conversación
ocurre vía eventos (conversation-engine); el gateway es de solo lectura
para estos recursos.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_session

router = APIRouter(prefix="/v1/conversations", tags=["conversations"])


@router.get("/")
async def list_conversations(
    tenant_id: UUID,
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT id, user_id, channel, status, started_at, ended_at
            FROM conversations
            WHERE tenant_id = :tenant_id
            ORDER BY started_at DESC
            LIMIT :limit
            """
        ),
        {"tenant_id": str(tenant_id), "limit": limit},
    )
    return [dict(row._mapping) for row in result.fetchall()]


@router.get("/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT id, role, content, created_at
            FROM messages
            WHERE conversation_id = :conversation_id
            ORDER BY created_at ASC
            """
        ),
        {"conversation_id": str(conversation_id)},
    )
    rows = [dict(row._mapping) for row in result.fetchall()]
    if not rows:
        raise HTTPException(status_code=404, detail="Conversación no encontrada o sin mensajes")
    return rows
