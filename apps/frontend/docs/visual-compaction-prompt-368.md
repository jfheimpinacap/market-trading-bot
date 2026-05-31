# Compactación visual operativa frontend-only (Prompt 368)

Objetivo: convertir la UI en un dashboard operativo más denso para debugging paper-only / live-read-only conservative sin tocar backend, policy, launcher, servicios Python, endpoints ni lógica de trading.

## Cambios aplicados

- **Tokens globales compactos:** se agregaron radios pequeños (`3px–6px`), sombras más livianas, botones/badges más bajos, tablas/listas más densas y menor padding en `panel`, `page-header`, cards y subsecciones.
- **Sidebar:** se redujo ancho/padding, se forzó ellipsis en labels largos, se corrigió overflow horizontal y el bloque `Advanced` ahora tiene scroll interno con altura acotada para evitar superposición visual.
- **Dashboard operativo:** se mantiene la vista executive/operator-first y se refuerzan grids compactos de 2–3 columnas, quick strip y KPIs de una fila en desktop, con fallback responsive.
- **Cockpit/Test Console:** el módulo de pruebas queda visualmente consolidado como `Operational Test Console`, centralizando perfiles, estado actual/último completado, acciones, progreso, exports/logs y JSON raw sin cambiar llamadas API ni polling.
- **Progreso/timer:** se representa el progreso disponible como barra estimada por fase usando los campos existentes (`current_phase`, `current_step`, `total_steps`, timestamps y elapsed). También se muestra timer de duración, último update y tiempo desde último progreso real/no-progress cuando está disponible.
- **Logs/export:** el log exportado y el JSON raw quedan en paneles scrollables compactos para no ocupar toda la pantalla.

## Nota de alcance

Este cambio es estrictamente frontend-only. No modifica contratos con backend ni decisiones de trading; solo reorganiza presentación, CSS, layouts y densidad visual para operación/debugging.
