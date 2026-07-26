-- =====================================================================
-- Netxia Conversational Platform (NCP) — Esquema inicial
-- Ejecutado automáticamente por el contenedor de Postgres en el primer
-- arranque (docker-entrypoint-initdb.d).
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "pgcrypto";  -- gen_random_uuid()

-- ---------------------------------------------------------------------
-- Multi-tenancy
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    subdomain TEXT UNIQUE NOT NULL,
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'tenant_viewer'
        CHECK (role IN ('platform_admin', 'tenant_admin', 'tenant_agent', 'tenant_viewer')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, email)
);

-- ---------------------------------------------------------------------
-- Canales de entrada
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS phone_numbers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    number TEXT NOT NULL,
    provider TEXT NOT NULL DEFAULT 'sip_trunk',
    enabled BOOLEAN NOT NULL DEFAULT true,
    UNIQUE (number)
);

CREATE TABLE IF NOT EXISTS whatsapp_instances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    phone_number_id UUID REFERENCES phone_numbers(id) ON DELETE SET NULL,
    session TEXT,
    enabled BOOLEAN NOT NULL DEFAULT true
);

-- ---------------------------------------------------------------------
-- Conversaciones
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,  -- número de teléfono o identificador externo
    channel TEXT NOT NULL CHECK (channel IN ('voice', 'whatsapp')),
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'resolved', 'escalated', 'abandoned')),
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_conversations_tenant_started
    ON conversations (tenant_id, started_at DESC);

CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    audio_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_messages_conversation
    ON messages (conversation_id, created_at ASC);

CREATE TABLE IF NOT EXISTS transcriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    confidence REAL
);

-- ---------------------------------------------------------------------
-- Spam
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS spam_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    phone_number TEXT NOT NULL,
    score REAL NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('blocked', 'flagged', 'allowed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_spam_logs_phone ON spam_logs (phone_number);

-- ---------------------------------------------------------------------
-- RAG (pgvector, 384 dims = paraphrase-multilingual-MiniLM-L12-v2)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rag_collections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS rag_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    collection_id UUID REFERENCES rag_collections(id) ON DELETE SET NULL,
    filename TEXT,
    content TEXT NOT NULL,
    embedding VECTOR(384) NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

-- Índice HNSW para búsqueda aproximada de vecinos más cercanos (coseno).
-- Se crea con lists conservador; ajustar `m`/`ef_construction` según
-- volumen real de documentos por tenant.
CREATE INDEX IF NOT EXISTS idx_rag_documents_embedding
    ON rag_documents USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_rag_documents_tenant ON rag_documents (tenant_id);

-- ---------------------------------------------------------------------
-- Integraciones CRM
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS crm_syncs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    crm_type TEXT NOT NULL CHECK (crm_type IN ('espocrm', 'suitecrm', 'odoo')),
    last_sync TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'ok', 'error'))
);

-- ---------------------------------------------------------------------
-- Datos semilla mínimos para desarrollo local
-- ---------------------------------------------------------------------
INSERT INTO tenants (id, name, subdomain)
VALUES ('00000000-0000-0000-0000-000000000001', 'Netxia Demo', 'demo')
ON CONFLICT (subdomain) DO NOTHING;
