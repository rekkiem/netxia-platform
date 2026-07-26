# ADR-002: RabbitMQ como Event Bus

## Estado
Aceptado

## Contexto
La arquitectura exige que todos los servicios se comuniquen mediante
eventos, nunca con llamadas síncronas acopladas.

## Decisión
Se elige **RabbitMQ** (exchange topic) sobre NATS para el MVP.

## Justificación
- Madurez y garantías de entrega (colas durables, ack manual) más
  simples de razonar que NATS JetStream para un equipo pequeño.
- Panel de administración web incluido, útil para debugging en
  operación diaria sin herramientas adicionales.
- Consumo de RAM aceptable para un VPS de bajo costo comparado con
  Kafka.

## Consecuencias
- Un único exchange (`netxia.events`) tipo topic centraliza todo el
  tráfico; cada servicio declara sus propias colas y bindings, lo que
  permite agregar consumidores nuevos sin tocar a los publishers.
- Si el volumen de eventos crece significativamente (>1000 msg/s
  sostenido), se reevaluará migrar a NATS o Kafka.
