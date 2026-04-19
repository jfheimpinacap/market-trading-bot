# Segunda pasada de compactación visual (Prompt 333)

Objetivo: reducir texto visible, altura de bloques, botones en pantalla y scroll sin cambiar lógica de negocio.

## Qué se compactó

- **Dashboard principal**
  - Header con estado operativo y acción avanzada bajo `Más`.
  - Resumen operator-first con menos campos visibles por defecto.
  - Lista de atención priorizada en top 2; resto bajo demanda.

- **Markets**
  - Etiqueta de filtros más corta y directa.
  - Acción secundaria de limpiar filtros agrupada en `Más` en el encabezado del bloque de mercados.

- **Portfolio**
  - Tarjetas de métricas con helper técnico movido a `Detalle` plegable por tarjeta.

- **Mission Control / Test Console base**
  - Botonera principal reducida a acciones críticas (`Start/Stop`).
  - Acciones secundarias agrupadas en `Más`.
  - Telemetría extensa movida a bloque plegable `Ver telemetría técnica completa`.

## Qué quedó bajo demanda

- Contexto ampliado del dashboard (evento, timestamps, hints/códigos).
- Alertas no prioritarias del dashboard.
- Helper textual de métricas del portfolio.
- Acciones operativas secundarias de Mission Control.
- Secciones de telemetría larga en Mission Control.

## Base responsive / móvil

- Menos dependencia de descripciones largas visibles.
- Menos controles simultáneos arriba de la pantalla.
- Más uso de secciones expandibles para reducir altura inicial.
- Mejor jerarquía visual: estado + KPIs + atención primero; detalle técnico después.
