# Roadmap — Netxia Conversational Platform

Este documento resume las mejoras planificadas después del MVP, en orden
de prioridad (P0 = próximo trimestre, P1 = corto plazo, P2-P3 = mediano/largo plazo).

## P0 — Impacto directo en calidad de experiencia

| Mejora | Descripción | Motivación |
|--------|-------------|------------|
| Migrar a Kokoro TTS | Reemplazar Piper por Kokoro | Voz notablemente más natural; Piper es funcional pero robótico en frases largas |
| Streaming de voz en tiempo real | Enviar audio a STT en chunks continuos en vez de esperar fin de turno completo | Reduce la latencia percibida de conversación de voz por debajo de 2s |
| Calibración de pesos del spam-filter con datos reales | Ajustar umbrales de `scorer.py` usando logs de producción | Las reglas actuales son conservadoras por diseño; se necesita data real para optimizar precisión/recall |

## P1 — Expansión funcional

| Mejora | Descripción |
|--------|-------------|
| Integración bidireccional con CRM (EspoCRM, Odoo) | Ya existen los 3 adaptadores; falta el flujo automático de sincronización post-conversación |
| Sentiment Analysis con modelo entrenado | Reemplazar el léxico simple de `sentiment.py` por un clasificador fine-tuneado en español chileno |
| Voice Biometrics | Identificar clientes recurrentes por huella de voz, sin depender solo del número entrante |
| Dashboard web para agentes humanos | UI sobre el gateway existente para gestionar derivaciones (`transfer.requested`) en tiempo real |

## P2 — Escalamiento y automatización comercial

| Mejora | Descripción |
|--------|-------------|
| Auto-provisioning de números | Que un tenant pueda comprar/activar un número SIP y una instancia WhatsApp desde el dashboard, sin intervención manual |
| Analytics avanzado | Heatmaps de conversación, funnels de conversión, insights por intención detectada |
| Multi-región / réplicas | Si un tenant crece mucho, replicar su base de datos vectorial (RAG) a un nodo dedicado |

## P3 — Expansión de plataforma

| Mejora | Descripción |
|--------|-------------|
| App móvil para agentes | Complemento nativo al dashboard web, con notificaciones push de derivaciones |
| Marketplace de integraciones | Que terceros puedan publicar adaptadores CRM/ERP adicionales siguiendo la interfaz `CRMAdapter` |
| Soporte multi-idioma | Extender STT/TTS/LLM más allá de español (inglés, portugués) para clientes con operación regional |

## Notas de arquitectura para el roadmap

- Todas las mejoras deben respetar el principio de **desacoplamiento
  total**: nuevos proveedores de LLM/TTS/STT/CRM se integran
  implementando la interfaz correspondiente, sin tocar el
  conversation-engine.
- Cualquier mejora que aumente el consumo de RAM/CPU debe reevaluarse
  contra el objetivo de costo operativo (< $30 USD/mes en el VPS base).
