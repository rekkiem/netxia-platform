# ADR-003: pgvector para RAG

## Estado
Aceptado

## Contexto
El bot necesita responder con información específica de cada tenant
(precios, políticas, FAQ) sin alucinar.

## Decisión
Se usa **pgvector** como extensión de PostgreSQL para almacenar
embeddings y hacer búsqueda de similitud, en vez de una base de datos
vectorial dedicada (Qdrant, Weaviate, Pinecone).

## Justificación
- Evita un componente de infraestructura adicional: ya se necesita
  PostgreSQL para el resto del dominio (conversaciones, tenants, etc.).
- Suficiente para el volumen esperado de documentos por tenant en el
  MVP (cientos a pocos miles de fragmentos).
- Índice HNSW nativo desde pgvector 0.5+ ofrece buen rendimiento de
  búsqueda aproximada sin operar un clúster separado.

## Consecuencias
- Si un tenant particular requiere millones de documentos indexados,
  se evaluará migrar ese tenant a una base vectorial dedicada
  (arquitectura ya lo permite, dado que RAG está encapsulado en
  `conversation-engine/app/rag.py`).
