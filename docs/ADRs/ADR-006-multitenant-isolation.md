# ADR-006: Multi-tenant con aislamiento por tenant_id

## Estado
Aceptado

## Contexto
La plataforma debe servir a múltiples empresas clientes desde la misma
infraestructura, sin fugas de datos entre ellas.

## Decisión
Se implementa **aislamiento lógico por `tenant_id`** (columna en cada
tabla + filtrado obligatorio en cada query), en vez de bases de datos
separadas por tenant o esquemas separados en Postgres.

## Justificación
- Simplicidad operativa: un único cluster de Postgres, Redis y
  RabbitMQ para todos los tenants, reduciendo drásticamente el costo de
  infraestructura (alineado con el objetivo de <$30 USD/mes).
- Las claves de Redis siempre incluyen `tenant_id` como parte del
  namespace (`conversation:{tenant_id}:{user_id}:...`).
- RabbitMQ: todos los eventos llevan `tenant_id` en el payload; los
  consumidores filtran o segmentan según corresponda.

## Consecuencias
- Requiere disciplina de desarrollo: **toda** query debe incluir el
  filtro `tenant_id`. Se documenta como regla de trabajo obligatoria
  (sección 9 del documento de arquitectura) y se recomienda agregar
  tests de integración específicos que verifiquen que un tenant nunca
  puede leer datos de otro.
- Si un cliente enterprise exige aislamiento físico (regulatorio), se
  puede migrar ese tenant específico a una instancia dedicada sin
  cambiar el modelo de datos.
