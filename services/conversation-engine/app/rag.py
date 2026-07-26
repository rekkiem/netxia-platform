"""
Retrieval-Augmented Generation sobre pgvector.

Estrategia: los documentos de cada tenant (`rag_documents`) se embeben con
sentence-transformers (modelo multilingüe, mismo usado en otros proyectos
de Netxia: paraphrase-multilingual-MiniLM-L12-v2, 384 dims) y se buscan por
similitud de coseno, filtrando siempre por tenant_id para mantener el
aislamiento multi-tenant.
"""
import logging
from uuid import UUID

from sentence_transformers import SentenceTransformer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("netxia.conversation-engine.rag")

EMBEDDING_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
TOP_K_DEFAULT = 4
MIN_SIMILARITY = 0.55  # documentos por debajo de este umbral se descartan

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info("Cargando modelo de embeddings %s", EMBEDDING_MODEL_NAME)
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _model


def embed_text(query: str) -> list[float]:
    return _get_model().encode(query, normalize_embeddings=True).tolist()


async def retrieve_relevant_snippets(
    session: AsyncSession,
    tenant_id: UUID,
    query: str,
    top_k: int = TOP_K_DEFAULT,
) -> list[str]:
    """Busca los `top_k` documentos más relevantes del tenant usando
    distancia de coseno (operador `<=>` de pgvector)."""
    embedding = embed_text(query)
    result = await session.execute(
        text(
            """
            SELECT content, 1 - (embedding <=> :query_embedding) AS similarity
            FROM rag_documents
            WHERE tenant_id = :tenant_id
            ORDER BY embedding <=> :query_embedding
            LIMIT :top_k
            """
        ),
        {"query_embedding": str(embedding), "tenant_id": str(tenant_id), "top_k": top_k},
    )
    rows = result.fetchall()
    return [row.content for row in rows if row.similarity >= MIN_SIMILARITY]
