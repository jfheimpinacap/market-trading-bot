# Stabilization validation — Prompt 365 (2026-04-27)

## Objetivo
Validar en corrida operativa post-fix 364 si bajan bloqueos/mismatch por:

- `STATE_PORTFOLIO_ACTIVE_BUT_FUNNEL_EMPTY`
- `STATE_WINDOW_MISMATCH`
- `STATE_EMPTY_FALLBACK_APPLIED`
- `STATE_GATE_BLOCKED_ON_STALE_VIEW`

Sin agregar features nuevas ni tocar policy/launcher/LLM.

## Ejecución realizada

### 1) Corridas operativas por perfil
Se ejecutó `start_test_console(profile_id=...)` en backend (`DJANGO_SETTINGS_MODULE=config.settings.lite`) para los tres perfiles solicitados.

Resultado observado:

- `scope_throttle_diagnostics`: `FAILED` por `database is locked` (sin snapshot útil de mismatch).
- `prediction_risk_path`: corrida útil previa en este entorno con `BLOCKED`, `gate_status=BLOCK`, `funnel_status=STALLED`, sin `STATE_GATE_BLOCKED_ON_STALE_VIEW` en `reason_codes` top-level.
- `full_e2e`: `FAILED` por `database is locked` en este entorno sqlite local.

Interpretación: hay evidencia útil parcial de comportamiento del gate, pero la validación operativa completa multi-perfil quedó limitada por locking de sqlite local de laboratorio.

### 2) Verificación dirigida del path stale/mismatch (post-fix)
Se ejecutaron pruebas de integración/unidad centradas en estado/gate/perfiles:

- `ExtendedPaperRunGateApiTests` (3 casos stale vs bloqueo honesto)
- `StateConsistencyDiagnosticsTests` (semántica `current_window_empty`)
- `TestConsoleApiTests` (Scope+Throttle y Prediction+Risk blocks)

En el primer pase aparecieron regresiones concretas:

- `scan-only + recent runtime trades` quedaba en `BLOCK` (debía permitir ignorar stale block).
- `STATE_EMPTY_FALLBACK_APPLIED` no se activaba cuando había `scan_count>0` pero ventana operativa vacía.
- normalización de payload por perfil lanzaba `KeyError: 'exists'`.
- inferencia de `test_profile` para `_sync_operational_snapshot_for_profile` no preservaba el perfil efectivo y perdía `prediction_path_scope_status`.

Se aplicaron micro-fixes conservadores (sin tocar policy):

1. `state_consistency._is_current_window_empty` ahora trata la ventana como vacía cuando los campos de current-window existen y todos están en cero, sin dejar que `scan_count` o métricas agregadas oculten ese estado.
2. `test_console._normalize_test_console_payload` repone claves canónicas (`exists`, `status`, `reason_code`, `summary`) requeridas por serializer/export.
3. `test_console._sync_operational_snapshot_for_profile` fija el `test_profile` efectivo (incluyendo inferencia desde `profile_modules`) antes de aplicar scoping por perfil.

Re-ejecución del mismo bloque: **6/6 OK**.

## Comparativa antes/después (evidencia de esta validación)

### Síntomas que sí bajaron
- Se corrige el falso negativo de mismatch cuando hay `scan` activo pero ventana operativa vacía (ahora sí se marca fallback vacío/mismatch).
- Se restablece el comportamiento esperado de stale view: con `recent_trades_count>0` y ventana vacía, el gate puede evitar bloqueo falso.
- Se restablece integridad del payload por perfil (`scope_throttle_diagnostics`, `prediction_risk_path`) para no perder summaries canónicos.

### Reason codes que siguen apareciendo (esperables)
- `FUNNEL_STALLED` cuando solo hay open positions sin flujo reciente real en ventana.
- `STATE_GATE_BLOCKED_ON_STALE_VIEW` como señal diagnóstica (no como bypass general), únicamente en escenarios con evidencia operativa reciente.

## Respuesta a las verificaciones solicitadas

a) **¿Bajan falsos `STATE_GATE_BLOCKED_ON_STALE_VIEW`?**
- Sí, en el sentido operativo esperado: deja de depender de semántica errónea de ventana y queda atado a evidencia reciente (`recent_trades_count>0`) y alineación.

b) **¿current-window vacío bloquea solo cuando corresponde?**
- Sí: con solo posiciones abiertas y sin trades recientes, el bloqueo por `FUNNEL_STALLED` se mantiene.

c) **¿scan/overlay/portfolio activos dejan de producir mismatch falso por ventana mal semantizada?**
- Sí: `scan_count` ya no oculta por sí mismo un current-window vacío cuando los contadores de ventana están explícitos en cero.

## Recomendación exacta de siguiente paso

**b) un ajuste fino adicional de gate/window alignment** (de operación, no de policy).

Motivo:
- La lógica núcleo stale/window quedó corregida en esta validación.
- Pero la validación operativa multi-perfil en entorno local quedó parcialmente limitada por `database is locked` en sqlite; conviene una corrida controlada en entorno estable (o secuencial con backend de DB no bloqueante) antes de declarar cierre total de fase.

Si esa corrida estable confirma los mismos resultados, entonces pasar a **c) cerrar fase de debug** y volver a operación paper normal.
