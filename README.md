# Netxia Conversational Platform (NCP) — MVP

Plataforma conversacional multi-tenant (CPaaS + Conversational AI) para
automatizar las comunicaciones de Netxia por **voz telefónica** y
**WhatsApp**, usando exclusivamente herramientas open source y
autohospedadas para mantener el costo operativo bajo control.

## Índice

- [Arquitectura](#arquitectura)
- [Stack tecnológico](#stack-tecnológico)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Instalación](#instalación)
- [Desarrollo local](#desarrollo-local-linuxmac-resumen-rápido)
- [Desarrollo local en Windows](#desarrollo-local-windows-11--docker-desktop--vscode-14gb-ram)
- [Tests](#tests)
- [Configuración de canales](#configuración-de-canales)
- [Observabilidad](#observabilidad)
- [Documentación adicional](#documentación-adicional)

## Arquitectura

Arquitectura **event-driven** de microservicios: ningún servicio llama
síncronamente a otro salvo el orquestador → llm-service (única
excepción, por necesidad de respuesta en el turno de conversación). Todo
lo demás se comunica vía eventos en RabbitMQ (exchange topic
`netxia.events`).

```
Llamada telefónica / WhatsApp
        │
        ▼
Asterisk (AudioSocket) / Evolution API
        │  eventos: voice.incoming / whatsapp.incoming
        ▼
   RabbitMQ (netxia.events)
        │
        ▼
Conversation Engine ──► LLM Service (router: fast/default/reasoning → Ollama)
        │                        │
        │                        ▼
        │                 RAG (pgvector) + Redis (memoria de contexto)
        │
        ▼  eventos: voice.outgoing / whatsapp.outgoing
Voice Service (TTS Piper) / WhatsApp Service (Evolution API)
        │
        ▼
   Respuesta al cliente
```

Ver diagramas completos (componentes, secuencia de llamada, secuencia de
WhatsApp) en `docs/architecture.md`.

## Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| Telefonía | Asterisk 20 + AudioSocket |
| WhatsApp | Evolution API (Baileys) |
| LLM | Ollama (Llama 3.2 3B / Gemma 2 2B / Mistral 7B) |
| STT | Faster Whisper |
| TTS | Piper |
| Base de datos | PostgreSQL 16 + pgvector |
| Cache / memoria | Redis 7 |
| Event bus | RabbitMQ 3.13 |
| IAM | Keycloak 25 |
| Automatización no crítica | n8n |
| Observabilidad | Prometheus + Grafana + Loki |
| Reverse proxy | Traefik 3 (SSL automático vía Let's Encrypt) |

Cada microservicio es un contenedor FastAPI independiente (Python 3.12),
construido con Docker Compose. Ver `services/*/requirements.txt` para
las versiones exactas de cada dependencia.

## Estructura del proyecto

```
netxia-platform/
├── docker-compose.yml       # Orquestación completa (22 servicios)
├── .env.example             # Variables de entorno documentadas
├── services/                # Microservicios (uno por carpeta)
│   ├── gateway/              # API pública (tenants, conversaciones)
│   ├── conversation-engine/  # Orquestador — el corazón del sistema
│   ├── voice-service/        # AudioSocket + STT + TTS + VAD
│   ├── whatsapp-service/     # Webhook + cliente Evolution API
│   ├── llm-service/          # Router de modelos Ollama
│   ├── spam-filter/          # Blacklist + scoring dinámico
│   ├── crm-service/          # Adaptadores EspoCRM/SuiteCRM/Odoo
│   ├── notification/         # Telegram + email (Web3Forms)
│   ├── identity/             # Validación JWT Keycloak + RBAC
│   ├── analytics/            # Métricas y reportes
│   └── shared/                # Config, eventos, clientes Redis/RabbitMQ/DB
├── config/                   # Configuración de Asterisk, Evolution, Traefik, Prometheus
├── scripts/                  # install.sh, deploy.sh, seed_db.py, init_db.sql
├── tests/                    # unit, integration, mocks
├── docs/                     # ADRs, roadmap, backlog, OpenAPI
└── .github/workflows/        # CI (lint+test+build) y CD (deploy SSH)
```

## Instalación

Requisitos: VPS con Ubuntu 24.04, al menos 8GB RAM (recomendado 16GB si
se usa Mistral 7B de forma habitual), acceso root.

```bash
git clone <repo> /opt/netxia
cd /opt/netxia
cp .env.example .env
nano .env   # completar credenciales reales

sudo bash scripts/install.sh
```

El script instala Docker, descarga los modelos LLM y la voz de Piper, y
levanta todos los servicios con `docker compose up -d --build`.

## Desarrollo local (Linux/Mac, resumen rápido)

```bash
cp .env.example .env   # valores por defecto sirven para desarrollo local
docker compose up -d postgres redis rabbitmq ollama
python scripts/seed_db.py   # crea tenant demo + documentos RAG de ejemplo
docker compose up -d --build
```

Cada servicio expone `/health` para verificar que está corriendo
correctamente. Si usas Windows, salta directamente a la sección
detallada más abajo («Desarrollo local (Windows 11 + Docker Desktop...)»),
que incluye mapeo de puertos y ajustes de memoria pensados para tu equipo.

## Tests

```bash
pip install -r requirements-dev.txt
pytest tests/ --cov=services --cov-report=term-missing
```

La suite incluye:
- **Tests unitarios** (`tests/unit/`): lógica pura sin dependencias de
  infraestructura — sentimiento, escalamiento, prompts, parser de
  WhatsApp, router de LLM, reglas de spam.
- **Tests de integración** (`tests/integration/`): flujo completo del
  `ConversationOrchestrator` con Redis y RabbitMQ mockeados.
- **Mocks reutilizables** (`tests/mocks/`): SIP/AudioSocket, webhook de
  WhatsApp, y cliente Ollama, para no depender de infraestructura real
  al testear.

Cobertura actual: **68%** sobre `services/`. El umbral de CI está
configurado en 65% (`pyproject.toml`), con `shared/rabbitmq.py` y
`shared/redis_client.py` por debajo del promedio porque requieren
infraestructura real para probarse a fondo (ver `docs/backlog.md`).

## Desarrollo local (Windows 11 + Docker Desktop + VSCode, 14GB RAM)

Este flujo usa un overlay (`docker-compose.local.yml`) que agrega
puertos al host y limita la memoria de Ollama, **sin modificar** el
`docker-compose.yml` que se usa en el VPS de producción.

### 0. Preparar Docker Desktop

- Usa el backend **WSL2** (Docker Desktop → Settings → General).
- Asigna memoria a Docker: Settings → Resources → Memory. Con 14GB
  totales en la máquina, deja **8-9GB para Docker** y el resto para
  Windows. Si usas `.wslconfig`, un ejemplo razonable:
  ```ini
  # C:\Users\<tu_usuario>\.wslconfig
  [wsl2]
  memory=9GB
  processors=4
  ```
  Reinicia WSL (`wsl --shutdown` en PowerShell) después de editarlo.

### 1. Clonar/descomprimir y configurar

```powershell
cd C:\proyectos
# (descomprime el zip aquí, o clona el repo)
cd netxia-platform
copy .env.example .env
notepad .env
```

En `.env`, para ahorrar RAM en tu máquina, deja el modelo de
"reasoning" apuntando a uno liviano en vez de Mistral 7B:
```
REASONING_LLM_MODEL=llama3.2:3b
```

### 2. Levantar el stack "core" (sin Asterisk/Evolution/observabilidad)

Los servicios de telefonía real, WhatsApp real, n8n y el stack de
observabilidad (Prometheus/Grafana/Loki) quedaron marcados como
**opcionales** (`profiles: ["full"]`) — no arrancan por defecto, así
ahorras RAM y evitas necesitar un troncal SIP o WhatsApp real solo para
probar el core conversacional.

```powershell
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d --build
```

Esto levanta: `postgres`, `redis`, `rabbitmq`, `ollama`, `keycloak`,
`gateway`, `identity`, `conversation-engine`, `llm-service`,
`whatsapp-service`, `voice-service`, `spam-filter`, `crm-service`,
`notification`, `analytics`.

### 3. Descargar modelos LLM

```powershell
docker compose exec ollama ollama pull gemma2:2b
docker compose exec ollama ollama pull llama3.2:3b
```

### 4. Seed de datos de prueba

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
python scripts\seed_db.py
```

### 5. Probar los endpoints desde Windows (curl/Postman/Thunder Client)

Gracias al overlay, cada servicio queda expuesto en localhost:

| Servicio | URL local |
|----------|-----------|
| Gateway | http://localhost:8001/health |
| Conversation Engine | http://localhost:8002/health |
| LLM Service | http://localhost:8003/health |
| WhatsApp Service | http://localhost:8004/health |
| Spam Filter | http://localhost:8005/health |
| CRM Service | http://localhost:8006/health |
| Notification | http://localhost:8007/health |
| Analytics | http://localhost:8008/health |
| Identity | http://localhost:8009/health |
| Voice Service | http://localhost:8010/health |
| Keycloak | http://localhost:8080 |
| RabbitMQ mgmt | http://localhost:15672 |
| Postgres | localhost:5432 (DBeaver/pgAdmin) |
| Redis | localhost:6379 (RedisInsight) |

```powershell
curl http://localhost:8003/health
```

### 6. Probar el flujo conversacional sin WhatsApp/Asterisk reales

Puedes simular un mensaje entrante de WhatsApp directamente contra el
`whatsapp-service`, sin necesitar Evolution API real:

```powershell
curl -X POST http://localhost:8004/webhook/00000000-0000-0000-0000-000000000001 `
  -H "Content-Type: application/json" `
  -d '{\"event\":\"messages.upsert\",\"instance\":\"demo\",\"data\":{\"key\":{\"remoteJid\":\"56912345678@s.whatsapp.net\",\"fromMe\":false,\"id\":\"TEST1\"},\"message\":{\"conversation\":\"Hola, quiero información\"}}}'
```

Revisa los logs del conversation-engine para ver el procesamiento:
```powershell
docker compose logs -f conversation-engine
```

### 7. Activar los servicios opcionales cuando los necesites

```powershell
# Todo, incluyendo Asterisk, Evolution API, n8n, Grafana/Prometheus/Loki, Traefik
docker compose -f docker-compose.yml -f docker-compose.local.yml --profile full up -d --build
```

### 8. Apagar todo

```powershell
docker compose -f docker-compose.yml -f docker-compose.local.yml down
# Agrega -v si además quieres borrar los volúmenes (datos de Postgres, etc.)
```

## Configuración de canales (producción, con SIP/WhatsApp reales)

### Número SIP (voz)

1. Contratar un troncal SIP con un proveedor chileno (DID +56 9).
2. Completar `SIP_USERNAME`, `SIP_PASSWORD`, `SIP_HOST` en `.env`.
3. Editar `config/asterisk/sip.conf` y `extensions.conf` con el número real.
4. Levantar Asterisk (perfil "full"): `docker compose --profile full up -d asterisk`.

### WhatsApp

1. Levantar Evolution API (perfil "full"): `docker compose --profile full up -d evolution-api`.
2. Escanear el código QR de vinculación (ver logs del contenedor o UI de
   Evolution API).
3. Verificar que el webhook apunta a `whatsapp-service` (ya configurado
   por defecto en `docker-compose.yml` vía `WEBHOOK_GLOBAL_URL`).

## Observabilidad

- Grafana: `https://monitor.netxia.cl` (usuario `admin`, password en `.env`)
- RabbitMQ management: `http://<ip>:15672`
- Logs centralizados: Loki, consultables desde Grafana

## Documentación adicional

- `docs/architecture.md` — Documento de arquitectura completo con diagramas
- `docs/ADRs/` — Decisiones de arquitectura documentadas (6 ADRs)
- `docs/roadmap.md` — Mejoras planificadas post-MVP
- `docs/backlog.md` — Backlog priorizado y deuda técnica conocida
- `docs/api/openapi.yaml` — Especificación OpenAPI del gateway

## Licencia

Ver archivo `LICENSE`.
