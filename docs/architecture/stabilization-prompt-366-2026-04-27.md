# Stabilization follow-up — Prompt 366 (2026-04-27)

## Objetivo
Ajuste fino conservador de `gate/window alignment` operativo para distinguir:

- bloqueo honesto por vista stale real (sin evidencia operativa reciente alineada), y
- degradación diagnóstica de stale-view cuando sí existe evidencia reciente alineada.

Sin cambios de policy de trading, sin launcher, sin features nuevas.

## Qué seguía bloqueando de más
Después de Prompt 364/365, `should_ignore_funnel_block` dependía de `recent_trades_count + current_window_empty + alignments`.
Faltaba exigir alineación operativa runtime real (`session_active`, `heartbeat_active`, `current_session_status`), por lo que algunos casos podían parecer stale-view degradable sin suficiente evidencia de sesión viva.

## Ajuste aplicado

### 1) Evidencia operativa reciente alineada (reutilizando campos existentes)
Se consolidó una evaluación explícita en `state_consistency` con:

- `recent_trades_count`
- `open_positions`
- `current_window_empty`
- `session_active`
- `heartbeat_active`
- `current_session_status`
- `session_alignment`
- `scope_alignment`
- `runtime_session_alignment`

`should_ignore_funnel_block` ahora solo es `true` cuando hay evidencia reciente alineada completa **y** ventana actual vacía.

### 2) Reason codes más explícitos
En gate:

- `STALE_VIEW_BLOCK_CONFIRMED_NO_RECENT_ALIGNED_EVIDENCE`
- `STALE_VIEW_BLOCK_DEGRADED_RECENT_ALIGNED_EVIDENCE`
- `STALE_VIEW_REVIEW_REQUIRED`
- `STATE_GATE_BLOCKED_ON_STALE_VIEW` se mantiene como diagnóstico cuando aplica degradación.

### 3) Observabilidad mínima adicional
`state_mismatch_summary` ahora incluye `recent_operational_evidence` con:

- `measurement_scope`: `rolling_60m_current_window_vs_runtime_portfolio`
- `source_of_truth`: funnel + portfolio + bootstrap
- detalle de evidencia usada/faltante

## Resultado esperado

- Menos falsos bloqueos dominados por `STATE_GATE_BLOCKED_ON_STALE_VIEW`.
- Se mantiene bloqueo conservador cuando solo hay posiciones abiertas o trades sin runtime activo alineado.
- No se habilita ejecución ni se inventan handoff/prediction/risk paths.

## Estado del plan
Este ajuste continúa el plan de debugging de estabilización (post 364/365) y deja el sistema listo para retomar pruebas operativas conservadoras si los checks E2E/Scope+Throttle siguen consistentes.
