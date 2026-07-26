"""
seed_db.py — Crea datos mínimos de prueba: un tenant demo, un número de
teléfono y un par de documentos RAG de ejemplo con sus embeddings.

Uso: python scripts/seed_db.py
Requiere las mismas variables de entorno que los servicios (.env cargado).
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "services"))

from sentence_transformers import SentenceTransformer  # noqa: E402
from sqlalchemy import text  # noqa: E402

from shared.database import session_scope  # noqa: E402

DEMO_TENANT_ID = "00000000-0000-0000-0000-000000000001"

SAMPLE_DOCUMENTS = [
    "Netxia ofrece consultoría en automatización de comunicaciones para empresas en Chile.",
    "El horario de atención de soporte es de lunes a viernes de 9:00 a 18:00 hora de Chile.",
    "Para solicitar una cotización, el cliente puede escribir por WhatsApp o llamar al número de contacto.",
]


async def seed() -> None:
    model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

    async with session_scope() as session:
        await session.execute(
            text(
                "INSERT INTO tenants (id, name, subdomain) VALUES (:id, 'Netxia Demo', 'demo') "
                "ON CONFLICT (subdomain) DO NOTHING"
            ),
            {"id": DEMO_TENANT_ID},
        )

        for doc in SAMPLE_DOCUMENTS:
            embedding = model.encode(doc, normalize_embeddings=True).tolist()
            await session.execute(
                text(
                    """
                    INSERT INTO rag_documents (tenant_id, filename, content, embedding)
                    VALUES (:tenant_id, 'seed.txt', :content, :embedding)
                    """
                ),
                {"tenant_id": DEMO_TENANT_ID, "content": doc, "embedding": str(embedding)},
            )

    print(f"Seed completado: tenant demo + {len(SAMPLE_DOCUMENTS)} documentos RAG.")


if __name__ == "__main__":
    asyncio.run(seed())
