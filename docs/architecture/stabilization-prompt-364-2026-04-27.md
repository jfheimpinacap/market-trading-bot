# Stabilization note — Prompt 364 (2026-04-27)

## Context
Prompt 364 continuó el plan de debugging de estabilización (no feature nueva, no refactor masivo) para corregir un desacople repetido entre estado operativo activo (`scan`/`overlay`/`portfolio`) y evaluación del funnel en la ventana actual que terminaba en bloqueos por vista stale.

## Causa raíz confirmada
Se identificó que `state_consistency` estaba evaluando “funnel vacío” solo con contadores de etapas agregadas (`scan_count`, `research_count`, `prediction_count`, `risk_decision_count`, `paper_execution_count`).

Ese criterio no coincidía con la semántica operativa de `current-window` usada downstream (handoff/prediction/risk/exec visibility), lo que permitía este patrón:

- `scan_count > 0` (actividad inicial viva)
- pero `shortlisted_signals/handoff/prediction/risk/execution candidates == 0` en la ventana operativa
- portfolio con runtime activo (especialmente `recent_trades_count > 0`)
- gate evaluando `funnel_status=STALLED` como bloqueo duro por funnel

Resultado: mismatch recurrente entre `active_operational_overlay_summary` y `gate_status`, con reason codes stale/mismatch en cascada.

## Corrección conservadora aplicada
Sin abrir bypass nuevo de policy ni cambiar launcher/LLM:

1. `state_consistency` ahora calcula `current_window_empty` con los mismos contadores operativos del handoff window (`shortlisted_signals`, `handoff_candidates`, `consensus_reviews`, `prediction_candidates`, `risk_decisions`, `paper_execution_candidates`), con fallback al criterio anterior si esos campos no existen.
2. `STATE_PORTFOLIO_ACTIVE_BUT_FUNNEL_EMPTY` y `STATE_EMPTY_FALLBACK_APPLIED` usan esta semántica de `current_window_empty`.
3. `should_ignore_funnel_block` se mantiene conservador: solo ignora bloqueo por funnel stale cuando hay evidencia de contexto operativo reciente (`recent_trades_count > 0`) además de `current_window_empty` y alineación de sesión/scope.

Con esto:

- Se reduce falso `STATE_GATE_BLOCKED_ON_STALE_VIEW` derivado de proyección de ventana inconsistente.
- Si no hay flujo actual real y tampoco evidencia reciente operativa, el gate sigue bloqueando honestamente.

## Observabilidad
Se mantiene la estructura existente de Test Console y export; la mejora principal es semántica de alineación state/window para que los reason codes reflejen mejor la realidad operativa, sin reescritura del panel.

## Cobertura de pruebas
Se agregaron pruebas para:

- `scan-only + recent runtime trades + ventana operativa vacía` => gate evita bloqueo stale falso.
- `solo open positions sin recent trades` => bloqueo se mantiene (`FUNNEL_STALLED`).
- `state_consistency` detecta correctamente fallback vacío incluso con `scan_count > 0` cuando la ventana operativa está vacía.
