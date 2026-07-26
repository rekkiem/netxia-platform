# ADR-005: Piper TTS sobre otras alternativas

## Estado
Aceptado

## Contexto
Se necesita síntesis de voz en español chileno/neutro, funcionando en
CPU (sin GPU disponible en el VPS objetivo), a costo cero.

## Decisión
Se usa **Piper TTS** sobre Coqui TTS o servicios cloud (Google/Amazon
Polly).

## Justificación
- Corre en tiempo real (~1x o mejor) en CPU sin necesitar GPU, crítico
  para cumplir el objetivo de latencia de llamada < 3s.
- Modelos de voz en español disponibles y livianos (decenas de MB).
- Sin costo por carácter/petición, a diferencia de Polly/Google TTS,
  alineado con el objetivo de costo operativo < $30 USD/mes.

## Consecuencias
- La calidad de voz de Piper es buena pero no al nivel de las voces
  neuronales de proveedores cloud premium. Se documenta como mejora
  futura (P0) migrar a Kokoro TTS cuando la calidad de voz se vuelva un
  diferenciador comercial relevante.
