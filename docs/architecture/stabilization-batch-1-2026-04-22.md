# Stabilization Batch 1 Completed (2026-04-22)

Referencias:
- Auditoría estructural base: `docs/architecture/stabilization-audit-2026-04-22.md`

## Quick wins elegidos para Batch 1

Este batch ejecuta únicamente quick wins seguros de Fase 1 (contracts/lifecycle), sin cambios de policy, launcher, LLM/training, ni refactor masivo.

1. **Contrato opcional consistente en frontend (status NO_RUN_YET no se colapsa a null)**
   - Se mantuvo compatibilidad con fallback legacy `404 -> null`.
   - Para respuestas `200` con `exists=false` / `status=NO_RUN_YET`, ahora se conserva el payload completo (`summary`, `reason_code`, `next_action_hint`) en vez de convertirlo a `null`.

2. **Unificación de query params en servicios Mission Control**
   - Se introdujo un helper común de `buildQuery(...)` para evitar divergencias por construcción manual repetida de `URLSearchParams`.

3. **Polling más estable (sin overlap de ticks)**
   - `usePollingTicker` ahora evita ejecutar una nueva iteración si la anterior sigue en curso, reduciendo refresh ambiguo y carreras por estado.

4. **Normalización de payload vacío opcional en backend views**
   - Se fortaleció el helper de payload vacío opcional para aceptar `next_action_hint` de forma explícita y reutilizable en smoke/trial status.

## Por qué estos primero

- Son cambios de **alto impacto y bajo riesgo** sobre síntomas repetitivos de lifecycle/contracts/polling.
- No introducen nuevas features ni alteran reglas de decisión/trading.
- Son acotados, compatibles y fáciles de validar con tests ya existentes.

## Qué síntomas deberían bajar con este batch

- Ambigüedad UI entre "sin corrida" vs "error real" en status opcionales.
- Divergencia accidental en query params entre endpoints similares.
- Estados intermitentes causados por polling concurrente cuando una llamada tarda más que el intervalo.
- Duplicación y drift en composición de payload vacío para estados opcionales.

## Pospuesto para Batch 2 / refactor mayor

### Batch 2 (mediano)
- Selector único reusable de "estado efectivo" para snapshots actuales vs históricos en todas las pantallas relevantes.
- Política de polling central por dominio (intervalos, stop conditions, visibility).
- Carga por dominios con boundaries de error en páginas de alta fan-out.

### Refactor mayor (posterior)
- Rebanar `test_console.py` y módulos monolíticos en capas.
- Consolidación profunda de serializers base y modularización de `views.py` por dominios.
