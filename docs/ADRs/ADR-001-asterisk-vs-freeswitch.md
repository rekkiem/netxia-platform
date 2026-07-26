# ADR-001: Elección de Asterisk sobre FreeSWITCH

## Estado
Aceptado

## Contexto
Se necesita un PBX open source capaz de recibir llamadas SIP y streamear
el audio en tiempo real hacia un servicio externo de IA (STT/LLM/TTS).

## Decisión
Se elige **Asterisk 20+** sobre FreeSWITCH.

## Justificación
- Asterisk soporta **AudioSocket** de forma nativa desde la versión 18,
  un protocolo TCP simple diseñado específicamente para streaming
  bidireccional con sistemas externos — encaja directamente con nuestra
  arquitectura basada en eventos.
- Ecosistema maduro en español/LatAm: abundante documentación y soporte
  comunitario para troncales SIP chilenas.
- FreePBX (interfaz gráfica) reduce la curva de aprendizaje para el
  equipo de operaciones sin sacrificar control programático vía ARI.

## Consecuencias
- Se depende del estado de AudioSocket en Asterisk 20 (ver Riesgo en
  sección 7 del documento de arquitectura); se mantiene un plan de
  fallback con RTP directo si AudioSocket resulta inestable.
- FreeSWITCH queda descartado para el MVP, pero podría reevaluarse si el
  volumen de llamadas concurrentes supera lo que Asterisk maneja bien en
  un VPS de bajo costo.
