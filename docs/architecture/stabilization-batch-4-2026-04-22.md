# Stabilization Batch 4 (2026-04-22)

## Scope (strict)

Batch 4 acotado de estabilización sobre **polling por dominio** para Mission Control/Test Console/Cockpit/Dashboard, sin features nuevas, sin cambios de policy, sin launcher y sin modularización grande.

## Ítems del audit/validación incluidos en este batch

Este batch toma explícitamente los puntos pendientes de:

- `stabilization-audit-2026-04-22.md` hotspot #6 (polling no centralizado por dominio) y foco Fase 2 (polling/state/UI sync).
- `stabilization-validation-after-batch-3-2026-04-22.md` foco recomendado para Batch 4:
  - intervalos por dominio,
  - stop conditions,
  - visibility handling,
  - freshness guards por identidad de run,
  - evitar mezcla/overwrite entre dominios.

### Cambios aplicados (batch pequeño, 5 ítems)

1. **Hook de polling endurecido con control de visibilidad/focus + backoff por idle.**
   - `usePollingTicker` ahora usa scheduler con `setTimeout` para evitar solapes, pausa cuando la pestaña no está visible y refresca al volver foco/visible.
   - Soporta `idle` y `stop` por tick para backoff conservador.

2. **Cadencia por dominio en Cockpit (sin reescribir la capa completa).**
   - Se separaron pollers para:
     - lifecycle/test-console status,
     - live-paper validation,
     - live-paper funnel/trial,
     - portfolio summary,
     - runtime attention.
   - Cada dominio usa intervalo base y techo de backoff distinto.

3. **Stop/idle conditions más claras para Test Console status.**
   - Polling de lifecycle queda activo con frecuencia alta cuando hay run activa y degrada a cadencia más lenta + backoff cuando no hay run.
   - Se mantiene antisolape (no overlap) por `inFlight` en el hook.

4. **Freshness guard por identidad de run en Cockpit status.**
   - `testConsoleStatus` ahora rechaza payloads más viejos cuando divergen `current_run_id/last_run_id` o cuando `updated_at` retrocede.
   - Reduce backsliding de estado por respuestas tardías.

5. **Alineación de Dashboard con refresco periódico conservador por dominio.**
   - Dashboard ahora hace polling de:
     - estado lifecycle/test-console,
     - resumen paper portfolio.
   - Con visibilidad/focus handling + backoff para bajar drift frente a Cockpit/Test Console.

## Síntomas que deberían bajar

- Drift de frecuencia entre Dashboard/Cockpit/Test Console para lifecycle básico.
- Polling activo innecesario cuando la vista no está visible.
- Sobrecarga por polling constante en estados idle/no-run.
- Retroceso a snapshot viejo por llegada tardía de payload de otro run.
- Inconsistencias transitorias entre paneles derivados de runtime attention y live-paper.

## Pospuesto explícitamente

Se mantiene pospuesto para la siguiente fase:

- modularización/refactor grande de Mission Control/Cockpit,
- polling policy global de toda la app con registry único,
- separación estructural completa de loaders por submódulo.

