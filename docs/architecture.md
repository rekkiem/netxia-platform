# Arquitectura — Netxia Conversational Platform

## 1. Diagrama de componentes

```mermaid
graph TB
    subgraph "Capa de Entrada"
        SIP[SIP Trunk / DID Chile +56 9]
        WA[WhatsApp Business]
    end

    subgraph "Capa de Orquestación"
        ASTERISK[Asterisk 20+ / FreePBX]
        EVOLUTION[Evolution API]
        TRAEFIK[Traefik / Reverse Proxy]
    end

    subgraph "Capa de Eventos"
        RABBIT[RabbitMQ]
        REDIS[Redis - Memoria/Caché]
    end

    subgraph "Capa de Servicios Core"
        CONV[Conversation Engine]
        VOICE[Voice Service]
        WA_SVC[WhatsApp Service]
        LLM[LLM Service - Router]
        STT[STT Service - Whisper]
        TTS[TTS Service - Piper]
        SPAM[Spam Filter Service]
    end

    subgraph "Capa de Persistencia"
        PG[(PostgreSQL + pgvector)]
    end

    subgraph "Capa de Automatización"
        N8N[n8n - Workflows]
    end

    subgraph "Capa de Observabilidad"
        GRAFANA[Grafana / Prometheus / Loki]
    end

    SIP --> ASTERISK
    WA --> EVOLUTION
    ASTERISK --> RABBIT
    EVOLUTION --> RABBIT
    RABBIT --> CONV
    CONV --> VOICE
    CONV --> WA_SVC
    CONV --> LLM
    VOICE --> STT
    VOICE --> TTS
    VOICE --> SPAM
    CONV --> PG
    CONV --> REDIS
    N8N --> RABBIT
    ASTERISK --> TRAEFIK
    EVOLUTION --> TRAEFIK
    CONV --> GRAFANA
```

## 2. Flujo de llamada telefónica

```mermaid
sequenceDiagram
    participant C as Cliente
    participant SIP as SIP Trunk
    participant AST as Asterisk/ARI
    participant AM as AudioSocket
    participant RABBIT as RabbitMQ
    participant CE as Conversation Engine
    participant STT as STT (Whisper)
    participant LLM as LLM Router
    participant TTS as TTS (Piper)
    participant PG as PostgreSQL

    C->>SIP: Llama al +569 XXXX XXXX
    SIP->>AST: Invite SIP
    AST->>AM: AudioSocket (streaming bidireccional)
    AM->>RABBIT: VoiceEvent (voice.incoming)
    RABBIT->>CE: Process VoiceEvent
    CE->>STT: (vía voice-service) transcribe audio
    STT->>CE: transcripción
    CE->>LLM: prompt + contexto + RAG
    LLM->>CE: respuesta
    CE->>RABBIT: VoiceEvent (voice.outgoing)
    RABBIT->>TTS: (vía voice-service) sintetiza audio
    TTS->>AM: audio
    AM->>AST: stream audio
    AST->>C: reproduce audio
    CE->>PG: guarda conversación
```

## 3. Flujo de WhatsApp

```mermaid
sequenceDiagram
    participant C as Cliente
    participant WA as WhatsApp
    participant EVO as Evolution API
    participant RABBIT as RabbitMQ
    participant CE as Conversation Engine
    participant LLM as LLM Router
    participant PG as PostgreSQL

    C->>WA: envía mensaje
    WA->>EVO: webhook
    EVO->>RABBIT: WhatsAppEvent (whatsapp.incoming)
    RABBIT->>CE: Process WhatsAppEvent
    CE->>LLM: prompt + contexto + RAG
    LLM->>CE: respuesta
    CE->>RABBIT: WhatsAppEvent (whatsapp.outgoing)
    RABBIT->>EVO: (vía whatsapp-service) send_message
    EVO->>WA: envía respuesta
    WA->>C: recibe mensaje
    CE->>PG: guarda conversación
```

## 4. Diagrama Entidad-Relación (resumen)

```mermaid
erDiagram
    TENANTS ||--o{ USERS : tiene
    TENANTS ||--o{ PHONE_NUMBERS : tiene
    TENANTS ||--o{ WHATSAPP_INSTANCES : tiene
    TENANTS ||--o{ CONVERSATIONS : tiene
    TENANTS ||--o{ RAG_DOCUMENTS : tiene
    TENANTS ||--o{ SPAM_LOGS : registra
    TENANTS ||--o{ CRM_SYNCS : sincroniza
    CONVERSATIONS ||--o{ MESSAGES : contiene
    MESSAGES ||--o| TRANSCRIPTIONS : puede_tener
    RAG_COLLECTIONS ||--o{ RAG_DOCUMENTS : agrupa

    TENANTS {
        uuid id PK
        text name
        text subdomain
        jsonb config
    }
    CONVERSATIONS {
        uuid id PK
        uuid tenant_id FK
        text user_id
        text channel
        text status
    }
    MESSAGES {
        uuid id PK
        uuid conversation_id FK
        text role
        text content
    }
    RAG_DOCUMENTS {
        uuid id PK
        uuid tenant_id FK
        text content
        vector embedding
    }
```

Ver el esquema SQL completo y ejecutable en `scripts/init_db.sql`.

## 5. Diagrama de despliegue (VPS único)

```mermaid
graph TB
    subgraph "VPS Ubuntu 24.04 (Docker Compose)"
        subgraph "Red pública (Traefik)"
            T[Traefik :80/:443]
        end
        subgraph "Servicios de aplicación"
            GW[gateway]
            CE[conversation-engine]
            LLMS[llm-service]
            VS[voice-service :8090]
            WS[whatsapp-service]
            SF[spam-filter]
            CRM[crm-service]
            NOT[notification]
            AN[analytics]
            ID[identity]
        end
        subgraph "Infraestructura"
            PG[(postgres:5432)]
            RD[(redis:6379)]
            RMQ[(rabbitmq:5672)]
            OL[ollama:11434]
            KC[keycloak:8080]
        end
        subgraph "Telefonía/Mensajería"
            AST[asterisk :5060/:8090]
            EVO[evolution-api]
        end
    end
    T --> GW
    T --> KC
    GW --> PG
    GW --> ID
    CE --> PG
    CE --> RD
    CE --> RMQ
    CE --> LLMS
    LLMS --> OL
    VS --> RMQ
    WS --> RMQ
    WS --> EVO
    AST --> VS
    SF --> RD
```
