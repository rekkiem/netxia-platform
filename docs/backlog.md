# Backlog — Netxia Conversational Platform

Lista de trabajo pendiente, más granular que el roadmap. Formato:
`[Prioridad] Título — Estimación — Notas`

## Alta prioridad (bloqueantes para producción real con clientes)

- [ ] **Validar AudioSocket en Asterisk 20 con tráfico real** — 2 días — Confirmar que el streaming bidireccional no se corta en llamadas >5 min (ver ADR-001 y riesgo asociado)
- [ ] **Cargar modelos LLM en Ollama en el arranque del VPS** — 0.5 días — Automatizar `ollama pull` dentro de `install.sh` para todos los modelos declarados en `.env`, no solo los dos actuales
- [ ] **Tests de aislamiento multi-tenant** — 1.5 días — Test de integración que verifique que el tenant A nunca puede leer conversaciones/documentos RAG del tenant B (crítico, ver ADR-006)
- [ ] **Rotar automáticamente el certificado ARI/SIP** — 0.5 días — Actualmente las contraseñas de `ari.conf`/`sip.conf` son estáticas; evaluar generación vía secretos de Docker

## Media prioridad

- [ ] **Endpoint de administración de documentos RAG** — 1 día — Actualmente `rag_documents` solo se puebla vía `seed_db.py`; falta un endpoint en el gateway para que cada tenant suba/actualice sus propios documentos
- [ ] **Retry con backoff exponencial en RabbitMQClient.connect** — 0.5 días — Actualmente el retry es con delay fijo de 3s; mejorar para entornos con arranque más lento
- [ ] **Rate limiting en el gateway** — 1 día — Proteger `/v1/tenants/` y `/v1/conversations/` de abuso, usando Redis como backend de conteo
- [ ] **Panel de RabbitMQ detrás de autenticación fuerte** — 0.5 días — El puerto 15672 está expuesto en el MVP; restringir por IP allowlist o quitarlo de la exposición pública
- [ ] **Migrar `andrius/asterisk:20` a una imagen propia versionada** — 1 día — Reducir dependencia de una imagen de terceros no mantenida oficialmente por el proyecto Asterisk

## Baja prioridad / mejoras incrementales

- [ ] **Soporte de DTMF en AudioSocket** — 1 día — El protocolo ya lo permite (`FrameType.DTMF`), falta implementar el manejo (ej. "presione 1 para ventas")
- [ ] **Cache de embeddings de RAG frecuentes** — 0.5 días — Evitar recalcular el embedding de preguntas muy repetidas (ej. "horario de atención")
- [ ] **Exportar métricas de Ollama a Prometheus** — 1 día — Tiempo de inferencia por modelo, para detectar degradación de latencia por modelo específico
- [ ] **Documentar procedimiento de rollback de deploy.sh** — 0.5 días — Actualmente `deploy.sh` no tiene rollback automático si el healthcheck falla tras el despliegue

## Deuda técnica conocida (documentada, no bloqueante)

- **[Corregido]** `docker-compose.yml` tenía un conflicto de puerto: tanto
  `asterisk` como `voice-service` mapeaban `8090:8090` al host. Se
  corrigió removiendo la publicación de ese puerto en `asterisk` (es
  Asterisk quien se conecta hacia `voice-service:8090`, no al revés).

- `voice-service/app/audiosocket.py`: el upsample de 8kHz a 16kHz es una
  duplicación simple de muestras, no un resampleo con filtro
  anti-aliasing. Suficiente para STT, pero debe mejorarse si se usa el
  mismo pipeline para otro propósito (ej. grabación de calidad).
- `spam-filter/app/scorer.py`: pesos de las reglas son heurísticos
  iniciales, pendientes de calibración con datos reales (ver P0 del
  roadmap).
- Cobertura de tests actual: 68% global. `shared/rabbitmq.py` y
  `shared/redis_client.py` tienen cobertura baja porque requieren
  infraestructura real (RabbitMQ/Redis) — se recomienda agregar tests
  de integración con contenedores efímeros (testcontainers) en una
  iteración futura.
