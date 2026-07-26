# ADR-004: Ollama como runtime de LLMs

## Estado
Aceptado

## Contexto
Se necesita correr modelos LLM open source localmente, sin depender de
APIs de terceros, para controlar costos y latencia.

## Decisión
Se usa **Ollama** como runtime de modelos (Llama 3.2 3B, Gemma 2 2B,
Mistral 7B).

## Justificación
- API HTTP simple y estable (`/api/chat`), fácil de envolver en
  `llm-service/app/ollama_client.py`.
- Gestión de descarga/cuantización de modelos integrada (GGUF),
  reduciendo el consumo de RAM para correr en un VPS modesto.
- Permite el patrón de "router de modelos" (fast/default/reasoning)
  cambiando solo el nombre del modelo en la llamada, sin reiniciar el
  servicio.

## Consecuencias
- Se requiere al menos 6-8GB de RAM disponibles para correr Mistral 7B
  cuantizado cómodamente junto al resto de los servicios; ver matriz de
  riesgos (sección 7 del documento de arquitectura).
