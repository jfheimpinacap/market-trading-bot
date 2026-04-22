# market-trading-bot

Professional initial scaffold for a modular prediction markets intelligence and paper-trading platform. This version is intentionally limited to project structure, local development tooling, a professional frontend shell, and a minimal backend healthcheck.

## Current scope

- **Frontend:** React + Vite + TypeScript local-first operator workspace with dashboard, markets, signals, risk, policy approval flow, paper trading, portfolio, post-mortem, automation, semi-auto demo, and system views.
- **Backend:** Django + Django REST Framework modular API with markets demo, signals demo, risk demo, policy engine demo, paper trading, post-mortem, automation, and health endpoints.
- **Position lifecycle:** new `position_manager` layer for open paper holding governance (HOLD/REDUCE/CLOSE/REVIEW_REQUIRED), auditable exit plans, mission-control integration, and operator-queue routing.
- **Research scan:** `research_agent` with RSS + Reddit + optional X/Twitter adapter ingestion, local LLM structured narrative analysis, social normalization, market linking, and mixed-source shortlist generation.
- **Infrastructure:** Docker Compose services for PostgreSQL and Redis.
- **Architecture:** monorepo organized for future apps, engines, provider adapters, and documentation.
- **Precedent-aware decision support (new):** research, prediction, risk, signal-fusion, and postmortem now consume semantic precedents automatically in internal flows with conservative influence and explicit audit trails (`AgentPrecedentUse`).

### Stabilization Batch 1 completed (2026-04-22)

Se ejecutó el primer batch acotado de estabilización de Fase 1, priorizando lifecycle/contracts/polling con cambios conservadores y compatibles (sin features nuevas ni cambios de policy).  
Detalle del batch: `docs/architecture/stabilization-batch-1-2026-04-22.md`.  
Auditoría base de referencia: `docs/architecture/stabilization-audit-2026-04-22.md`.

### Stabilization Batch 2 completed (2026-04-22)

Se ejecutó Batch 2 de estabilización media sobre lifecycle/contracts de Mission Control + Test Console + Cockpit, enfocado en separar de forma canónica current run vs last completed run y reducir shaping redundante de status sin introducir features nuevas.  
Detalle del batch: `docs/architecture/stabilization-batch-2-2026-04-22.md`.  
Referencias enlazadas: auditoría base `docs/architecture/stabilization-audit-2026-04-22.md` + Batch 1 `docs/architecture/stabilization-batch-1-2026-04-22.md`.

### Stabilization validation after Batch 2 (2026-04-22)

Se ejecutó una validación de estabilización (sin features nuevas ni refactor masivo) para medir reducción real de síntomas en contratos/lifecycle entre Mission Control, Cockpit, Test Console y Dashboard.  
Reporte corto de hallazgos residuales y foco recomendado para Batch 3: `docs/architecture/stabilization-validation-after-batch-2-2026-04-22.md`.

### Test Console lifecycle hardening for real-progress hangs (Prompt 352)

Mission Control Test Console lifecycle now distinguishes **real pipeline progress** from **refresh noise** so runs cannot stay `RUNNING` indefinitely due to minor snapshot churn.

- Hang timeout now uses `last_real_progress_at` (phase/step/event pipeline progress), not generic payload refresh activity.
- Status refreshes that only update secondary telemetry are tracked as non-progress via:
  - `last_non_progress_refresh_at`
  - `hang_reason_classification`
- Canonical lifecycle flags are now exposed for UI safety:
  - `is_terminal`
  - `is_hung`
  - `can_stop`
- `Stop test` enablement is now based on non-terminal run state (`can_stop`) rather than narrow/ambiguous UI-only conditions.
- Validation/gate stuck states (including reused safe session bootstrap paths) now converge to timeout classification when no real progress occurs, even if polling/refresh traffic continues.

### Dashboard operator-first compact layout (Prompt 329)

The main dashboard was compacted for operator-first scanning with less vertical noise and less default explanatory text.

- Added a top compact status strip for bot state, funnel, validation, gate, trial, and attention mode.
- Prioritized at-a-glance operator blocks: latest useful signal, active exposure, relevant blocking, and warning focus.
- Moved technical/verbose context into collapsible detail sections while preserving navigation to advanced cockpit views.
- Reduced card padding/height and tightened KPI presentation to lower scroll and improve responsive stacking behavior.

### Secondary views transversal visual cleanup (Prompt 330)

Secondary views now follow the same compact operator-first visual hierarchy used by dashboard improvements:

- **Markets** now keeps summary metrics on top and moves filter tooling into a compact collapsible block (auto-open when filters are active).
- **Portfolio** now prioritizes account metrics + equity + positions + trades in the default flow, with account internals/review bridge kept in collapsible technical detail sections.
- **Advanced/Cockpit** now prioritizes primary mission controls and moves secondary manual actions into an expandable section.
- Shared compact UI adjustments were applied across equivalent secondary layouts (`markets`, `portfolio`, `cockpit`, `mission-control` patterns):
  - tighter panel/action spacing,
  - reduced default descriptive text noise,
  - denser buttons/tables/cards for lower scroll and cleaner responsive base.

### Navigation/revalidation UX hardening (Prompt 340)

Dashboard, Markets, and Portfolio now keep the **last valid payload visible** while revalidating in the background during internal navigation/focus refreshes.

- `DataStateWrapper` now supports stale-while-revalidate behavior (`hasData` + `staleWhileRevalidate`) so a block only shows full loading/error states when it has no usable prior data.
- Dashboard, Markets, and Portfolio loaders now preserve previously successful data on transient refresh failures instead of clearing the UI back to an empty loading state.
- Markets filter refresh keeps the prior event catalog when a filter-triggered event reload fails, reducing route-change and filter-change flicker.
- Result: internal route changes no longer depend on manual browser refresh to quickly recover a usable view when cached valid data exists.


### Mission Control Ollama shadow analyst (Prompt 289)

Mission Control/Test Console now includes an **Ollama local shadow analyst** path that reads real pipeline artifacts, emits a compact `llm_shadow_summary` in status/export payloads, and persists each shadow output as a reusable historical backend artifact.

- Scope is strict shadow mode only:
  - advisory-only, non-blocking;
  - does **not** change scoring/gating/risk/execution;
  - does **not** create trades;
  - remains strict `REAL_READ_ONLY` + `PAPER_ONLY`.
- Config (local env):
  - `OLLAMA_ENABLED` (or `LLM_ENABLED`) to enable/disable shadow analysis.
  - `OLLAMA_BASE_URL` (default `http://localhost:11434`).
  - `OLLAMA_MODEL` (alias for `OLLAMA_CHAT_MODEL`).
  - `OLLAMA_TIMEOUT_SECONDS`.
- Failure mode is safe:
  - if Ollama is down/unreachable/timeout/invalid response, the pipeline continues and reports `llm_shadow_reasoning_status=DEGRADED|UNAVAILABLE`.
  - degraded/unavailable snapshots can also be persisted as non-blocking historical artifacts.
- Export/status now includes compact fields:
  - `provider`, `model`, `llm_shadow_reasoning_status`, `stance`, `confidence`,
  - `recommendation_mode`, `summary`, `key_risks`, `key_supporting_points`,
  - plus explicit shadow safety flags (`shadow_only`, `advisory_only`, `non_blocking`),
  - plus historical references (`latest_llm_shadow_summary`, `llm_shadow_history_count`, `llm_shadow_recent_history`).
- Persisted artifact associations (when available) include: `market_id`, `handoff_id`, `prediction_candidate_id`, `risk_decision_id`, `shortlist_signal_id`, runtime session reference, and source scope/preset.

### Mission Control Ollama auxiliary signal (Prompt 290)

Mission Control/Test Console now adds an explicit **paper-only auxiliary signal** layer (`llm_aux_signal_summary`) that reuses persisted shadow outputs (`latest_llm_shadow_summary` / `LlmShadowAnalysisArtifact`) as an auditable review-priority hint.

- Toggle (default conservative):
  - `OLLAMA_AUX_SIGNAL_ENABLED=false` by default.
- Contract is strictly non-execution:
  - advisory-only;
  - `affects_execution=false`;
  - no sizing/dispatch/final-trade mutation;
  - keeps `REAL_READ_ONLY` + `PAPER_ONLY`.
- Status/export now include compact auxiliary fields:
  - `enabled`, `source_artifact_id`, `aux_signal_status`, `aux_signal_recommendation`,
  - `aux_signal_reason_codes`, `aux_signal_weight`,
  - plus explicit safety flags (`advisory_only=true`, `affects_execution=false`, `paper_only=true`).

### Mission Control observability hardening (Prompt 267)

Backend Mission Control observability now degrades safely (HTTP 200) when paper-only runtime rejects a final trade (for example insufficient paper cash), instead of bubbling an unhandled exception from funnel/gate/status/export GET flows.

- Final paper-trade bridge now captures expected `PaperTradingRejectionError` as explicit diagnostics.
- Compact reason codes now include runtime-rejection intent, such as:
  - `PAPER_TRADE_FINAL_BLOCKED_BY_CASH`
  - `PAPER_TRADE_FINAL_BLOCKED_BY_REJECTION`
  - `PAPER_TRADE_FINAL_RUNTIME_REJECTION_CAPTURED`
  - `PAPER_TRADE_FINAL_BLOCKED_BY_RUNTIME`
- Diagnostics are surfaced in existing summaries (`paper_trade_summary`, `paper_trade_final_summary`, `execution_lineage_summary`) plus compact runtime rejection fields.

Test Console export reconciliation is now `None`-safe for numeric portfolio metrics (`equity`, `unrealized_pnl`, `realized_pnl`, `recent_trades_count`, `open_positions`), with explicit degraded reporting instead of `TypeError`.

- Reconciliation reason codes now include:
  - `PORTFOLIO_TRADE_RECONCILIATION_OK`
  - `PORTFOLIO_TRADE_RECONCILIATION_DEGRADED`
  - `PORTFOLIO_TRADE_RECONCILIATION_MISSING_NUMERIC_FIELD`
  - `PORTFOLIO_TRADE_RECONCILIATION_FALLBACK_USED`

Scope remains unchanged: observability-first, `REAL_READ_ONLY` market data, and `PAPER_ONLY` execution (no live broker/real-money enablement).

### Mission Control cash-pressure + final fan-out diagnostics (Prompt 268)

Mission Control backend now emits compact operational truth for the final paper-trade materialization stage without changing selection/execution logic.

- New `cash_pressure_summary` + `cash_pressure_examples` are included in funnel snapshot and Test Console export log.
- `cash_pressure_summary` reports:
  - `cash_available`
  - `executable_candidates`
  - `estimated_cash_required`
  - `candidates_at_risk_by_cash` (potential pressure)
  - `candidates_blocked_by_cash_precheck` (effective cash blocking)
  - `candidates_blocked_by_active_position` (effective non-cash dominant blocking)
  - `candidates_blocked_by_cash` (compat field, now aligned to effective cash precheck blocking)
  - `candidates_reused`
  - `cash_pressure_status`
  - `cash_pressure_reason_codes`
- Cash pressure reason codes include explicit differentiation between normal/reuse and pressure/fanout contexts (for example `CASH_PRESSURE_INSUFFICIENT_FOR_ALL`, `CASH_PRESSURE_BLOCKING_FINAL_TRADES`, `CASH_PRESSURE_FANOUT_EXCESSIVE`).
- Existing `final_fanout_summary` stays logic-neutral and is now consumed alongside cash pressure to distinguish:
  - real cash insufficiency,
  - excessive lineage/market fan-out,
  - expected healthy reuse.

Scope remains observability-first and paper-only (`REAL_READ_ONLY` + `PAPER_ONLY`), with no runtime rewrite and no live-trading enablement.

### Mission Control cash-aware final precheck (Prompt 271)

Mission Control backend now adds a conservative **cash-aware precheck** right before final paper-trade materialization.

- Goal: avoid late runtime rejections when candidates are already known to exceed available paper cash.
- Rule is intentionally simple/stable (no optimizer):
  - iterate executable final candidates in stable order,
  - select while cash budget allows,
  - defer/block remaining candidates once budget is insufficient.
- New reason codes in the same existing diagnostic flow include:
  - `PAPER_TRADE_SELECTED_FOR_EXECUTION`
  - `PAPER_TRADE_BLOCKED_BY_CASH_PRECHECK`
  - `PAPER_TRADE_DEFERRED_BY_CASH_BUDGET`
  - `PAPER_TRADE_CASH_BUDGET_EXHAUSTED`
  - `PAPER_TRADE_FINAL_BLOCKED_BY_CASH`
- Existing summaries/export now explicitly surface:
  - `cash_available`
  - `executable_candidates`
  - `selected_for_execution`
  - `blocked_by_cash_precheck`
  - `deferred_by_budget`
  - `cash_throttle_reason_codes`

Clarification: this precheck is **before** `execute_paper_trade`; runtime cash rejection is still captured separately if it happens (for example due concurrent cash changes). Scope remains observability-first and strictly `REAL_READ_ONLY` + `PAPER_ONLY` (no live trading).

### Mission Control active-position conservative gate (Prompt 272)

Mission Control backend now adds a conservative **active position / active trade gate** before final paper-trade materialization to contain redundant buy-side fan-out.

- Rule (stable, minimal):
  - if the same market/lineage already has active exposure, skip additive new-entry materialization;
  - allow reduce/exit-shaped candidates to bypass this gate;
  - keep reuse preference for existing trade/dispatch/position artifacts.
- New diagnostics are emitted in existing funnel/export summaries (no parallel logging), including:
  - `PAPER_TRADE_BLOCKED_BY_ACTIVE_POSITION`
  - `PAPER_TRADE_BLOCKED_BY_EXISTING_OPEN_TRADE`
  - `PAPER_TRADE_SKIPPED_BY_POSITION_EXPOSURE`
  - `PAPER_TRADE_POSITION_GATE_APPLIED`
  - `PAPER_TRADE_ALLOWED_REDUCE_POSITION`
  - `PAPER_TRADE_ALLOWED_EXIT_POSITION`
  - `PAPER_TRADE_POSITION_GATE_BYPASSED_FOR_EXIT`
- New compact block:
  - `position_exposure_summary` (`open_positions_detected`, blocked/allowed counters, reason codes).
  - Uses the same source of truth as `final_trade_position_gate` (final-trade bridge counters + portfolio exposure context), so it stays aligned with `paper_trade_final_summary`.
  - Snapshot/export/status serializers now propagate that same object end-to-end (no late zero-default reconstruction), so `paper_trade_final_summary` and `position_exposure_summary` stay consistent in text/json exports.
  - Includes normalized position reason codes (`POSITION_EXPOSURE_*`), including active position presence, existing open trade lineage, exit bypass, and no-exposure paths.

Cash vs exposure clarification:
- **Active-position gate** blocks redundant additive exposure before cash pressure is hit.
- **Cash precheck** still handles remaining selected candidates against available paper cash.

Final diagnostic hierarchy clarification:
- `paper_trade_final_summary` now publishes `dominant_blocking_gate` and `secondary_pressure`.
- If candidates are blocked by position exposure before cash precheck, that gate is the dominant blocker.
- Cash pressure remains visible as potential secondary pressure (`candidates_at_risk_by_cash`) without double-counting as effective cash blocking.

Scope remains unchanged: observability-first, backend-only, `REAL_READ_ONLY` + `PAPER_ONLY`.

### Mission Control position-exposure final propagation fix (Prompt 277)

Backend-only fix to remove the last-mile contradiction where `paper_trade_final_summary` showed active-position blocking but `position_exposure_summary` could still appear as zeroed defaults in final status/export payloads.

- `position_exposure_summary` is now forwarded from the same final-gate source in `live_paper_autonomy_funnel` handoff diagnostics (no late omission/default replacement).
- Test Console status and export consume that same propagated object, keeping text/json output aligned with:
  - `paper_trade_final_summary`
  - `portfolio_summary`
  - `cash_pressure_summary`
- No gate policy changes were introduced (active-position gate, cash precheck, and fan-out logic remain unchanged).
- Safety boundary remains strict: observability-first with `REAL_READ_ONLY` + `PAPER_ONLY` (no live trading enablement).

### Mission Control early execution-promotion exposure gate (Prompts 279–280)

Backend Mission Control now applies a **small early pre-filter** in `_build_paper_execution_diagnostics` right before promoting executable intake candidates to execution decision stage.

- Purpose: suppress redundant additive promotion when active exposure already exists for the same market/lineage.
- Behavior:
  - suppress additive promotion with active market position:
    - `EXECUTION_PROMOTION_SUPPRESSED_BY_ACTIVE_POSITION`
  - suppress additive promotion with existing open-trade lineage:
    - `EXECUTION_PROMOTION_SUPPRESSED_BY_EXISTING_OPEN_TRADE`
  - allow reduce/exit-shaped candidates:
    - `EXECUTION_PROMOTION_ALLOWED_FOR_EXIT`
  - allow candidates without active exposure:
    - `EXECUTION_PROMOTION_ALLOWED_WITHOUT_EXPOSURE`
- New compact diagnostics blocks:
  - `execution_promotion_gate_summary` now separates:
    - `candidates_visible` (execution-stage visible candidates),
    - `candidates_promoted_to_decision` (subset actually promoted downstream),
    - `candidates_suppressed_by_active_position` / `candidates_suppressed_by_existing_open_trade`,
    - `candidates_allowed_for_exit` / `candidates_allowed_without_exposure`,
    - `execution_promotion_gate_reason_codes`.
  - `execution_promotion_gate_examples` (compact examples, max 3).
- Operational semantics clarification:
  - `paper_execution_candidates` remains the visible execution-stage count;
  - promoted/suppressed counters are explicit in the promotion-gate block and mirrored in `execution_lineage_summary`.
- Clarification:
  - this is an **early promotion suppression** to reduce downstream decision/dispatch/final-fanout pressure;
  - the existing final exposure gate remains unchanged and still acts as final safety backstop.

Scope remains backend-only, observability-first, and strict `REAL_READ_ONLY` + `PAPER_ONLY` (no live trading enablement).

### Mission Control execution-candidate creation gate (Prompt 281)

Backend Mission Control now adds a **pre-creation exposure gate** when bridging readiness artifacts into `AutonomousExecutionIntakeCandidate`.

- What changed:
  - additive candidates are now suppressed **before creation** when active exposure is already present for the same market/lineage.
  - reduce/exit shapes remain allowed and are still created/promoted.
- New compact observability block:
  - `execution_candidate_creation_gate_summary`:
    - `candidates_suppressed_before_creation`
    - `candidates_created`
    - `candidates_allowed_for_exit`
    - `candidates_allowed_without_exposure`
    - `execution_candidate_creation_gate_reason_codes`
  - `execution_candidate_creation_gate_examples` (compact, max 3).
- How to read both gates now:
  - **creation gate** = suppression before `AutonomousExecutionIntakeCandidate` exists (visibility pressure reduction).
  - **promotion gate** = suppression after candidate is visible, before decision/dispatch/final.
- Expected effect:
  - lower redundant `paper_execution_candidates`,
  - lower downstream lineage/decision/dispatch pressure,
  - `execution_promotion_gate_summary` semantics stay intact.

Scope stays backend-only, observability-first, and strict `REAL_READ_ONLY` + `PAPER_ONLY` (no `/runtime` rewrite, no live trading enablement).

### Mission Control execution-stage semantic alignment (Prompt 282)

Backend Mission Control now aligns execution-stage summaries with pre-creation suppression semantics so readiness artifacts are no longer counted as created/visible execution candidates.

- Semantic split is now explicit:
  - `route_created` / `route_reused` in `paper_execution_summary` refer to **AutonomousExecutionReadiness** lifecycle.
  - `created` / `reused` / `visible` / `hidden` in `paper_execution_visibility_summary` refer to **AutonomousExecutionIntakeCandidate** lifecycle only.
  - `missing` in visibility summary means readiness exists but candidate was not created (for example suppression before creation).
- Reason codes were aligned to avoid false “candidate created” interpretation:
  - `PAPER_EXECUTION_READINESS_CREATED`
  - `PAPER_EXECUTION_READINESS_REUSED`
  - `PAPER_EXECUTION_CANDIDATE_NOT_CREATED_DUE_TO_SUPPRESSION`
  - `PAPER_EXECUTION_CREATED` is no longer used for readiness-only events.
- `execution_artifact_summary`, `paper_execution_visibility_summary`, and `execution_candidate_creation_gate_summary` now tell the same operational story when pre-creation suppression is active.

Scope remains backend-only, observability-first, and strict `REAL_READ_ONLY` + `PAPER_ONLY` (no frontend/runtime changes and no live trading enablement).

### Mission Control execution reason-code prioritization (Prompt 283)

Backend Mission Control now prioritizes suppression semantics when readiness exists but candidate creation was suppressed **before creation**.

- Reason-code priority update (no logic changes to gates/runtime):
  - dominant reason remains `PAPER_EXECUTION_CANDIDATE_NOT_CREATED_DUE_TO_SUPPRESSION` (+ `PAPER_EXECUTION_READINESS_WITHOUT_CANDIDATE`) when suppression is the real cause.
  - `PAPER_EXECUTION_CANDIDATE_SOURCE_MODEL_MISMATCH` is now reserved for actual artifact/source mismatch cases.
- Coherency intent:
  - `paper_execution_visibility_summary`,
  - `execution_artifact_summary`,
  - `execution_candidate_creation_gate_summary`
  now narrate the same suppression-first story without noisy mismatch labeling.

Scope remains backend-only, observability-first, and strict `REAL_READ_ONLY` + `PAPER_ONLY` (no frontend/runtime changes and no live trading enablement).

### Mission Control internal consolidation pass (Prompt 285)

Final backend-only cleanup pass to reduce diagnostic duplication and clarify internal semantics without changing pipeline behavior.

- `live_paper_autonomy_funnel`:
  - consolidated repeated lineage-anchor resolution used by readiness/candidate lifecycles into one internal helper;
  - consolidated repeated reason-code de-duplication into one helper (`_unique_codes`) used across dispatch/final-trade/summary assembly paths;
  - kept backward-compatible promotion-gate aliases (`suppressed_by_active_position`, `suppressed_by_existing_open_trade`, `allowed_for_exit`, `allowed_without_exposure`) while preserving the canonical `candidates_*` fields as source of truth.
- `test_console`:
  - consolidated repeated funnel field coercion (`int`/`str`/`list`) into shared helpers for snapshot assembly;
  - reduced repeated summary mapping boilerplate for execution/trade diagnostic blocks.
- No business-logic or gate-policy changes:
  - no changes to cash precheck, suppression-before-promotion, suppression-before-creation, final gate behavior, runtime mode, or frontend.

Safety boundary remains strict: observability-first with `REAL_READ_ONLY` + `PAPER_ONLY`.

### Scan diagnostics + demo narrative fallback (backend, local V1 paper)

`research_agent` scan runs now persist explicit diagnostics in `SourceScanRun.metadata.scan_diagnostics` so local V1 paper tests can explain zero-signal stalls instead of failing silently.

- diagnostics include:
  - `source_mode`
  - `rss_enabled` / `reddit_enabled` / `x_enabled`
  - `rss_fetch_attempted` / `reddit_fetch_attempted` / `x_fetch_attempted`
  - `zero_signal_reason_codes`
  - `diagnostic_summary`
- compact reason codes used:
  - `NO_RSS_SOURCE_CONFIGURED`
  - `NO_REDDIT_SOURCE_CONFIGURED`
  - `NO_X_SOURCE_CONFIGURED`
  - `ALL_SOURCES_EMPTY`
  - `DEMO_MODE_NO_NARRATIVE_FIXTURES`
  - `DEMO_FALLBACK_USED`
  - `DEMO_FALLBACK_DISABLED`

For local/demo runs only, an optional deterministic fallback can generate a small synthetic narrative intake from eligible demo paper-tradable markets when real narrative sources are empty. Synthetic signals are clearly marked in metadata/reason codes (`is_demo`, `is_synthetic`, `is_fallback`, `DEMO_SYNTHETIC_FALLBACK`) and source labels (`DEMO_NARRATIVE_*`) so they are not confused with RSS/Reddit/X.

Config toggle:
- `SCAN_DEMO_NARRATIVE_FALLBACK_ENABLED`
  - default: `true` in `local`/`test`
  - default: `false` otherwise

This is strictly for unblocking local V1 paper pipeline testing and does **not** enable live trading or real-money execution.

### Shortlist → handoff market-link diagnostics (backend, V1 paper/local-test)

Mission Control export logs now include a compact `market_link_summary` block to explain exactly why shortlisted signals do or do not reach handoff:

- `shortlisted_signals`
- `market_link_attempted`
- `market_link_resolved`
- `market_link_missing`
- `market_link_ambiguous`
- `market_link_reason_codes` + `market_link_examples` (max 3)

`research_agent` market inference was also tightened conservatively to reduce false negatives in demo/local topics while still refusing ambiguous ties. The flow remains observability-first and strictly `REAL_READ_ONLY + PAPER_ONLY` (no live execution enablement).

### Downstream route diagnostics (market link OK, handoff still missing)

Mission Control funnel/Test Console now also emits `downstream_route_summary` so “linked but no handoff” is explicit instead of hidden behind generic blockage:

- `route_expected`
- `route_available`
- `route_missing`
- `route_attempted`
- `route_created`
- `route_blocked`
- `downstream_route_reason_codes`
- `downstream_route_examples` (max 3: `signal_id`, `market_id`, `expected_route`, `reason_code`)

This is observability-first for V1 local/test paper runs and keeps strict boundaries (`REAL_READ_ONLY + PAPER_ONLY`). It does not bypass consensus/risk/policy/safety guardrails.

### Live Read-Only Paper Autopilot Bootstrap (backend, new)

`mission_control` now exposes a compact backend bootstrap for autonomous paper sessions using real-market read-only data without enabling live trading execution.

- preset: `live_read_only_paper_conservative`
- guarantees:
  - `market_data_mode = REAL_READ_ONLY`
  - `paper_execution_mode = PAPER_ONLY`
  - no real-money/live execution routes enabled
  - reuses existing mission-control runtime session + heartbeat runner (no new scheduler)
- API:
  - `POST /api/mission-control/bootstrap-live-paper-session/`
  - `GET /api/mission-control/live-paper-bootstrap-status/`

### Live Paper Autopilot cockpit card (frontend, new)

`/cockpit` now includes a compact **Live Paper Autopilot** card that consumes the backend bootstrap/status endpoints directly:

- `GET /api/mission-control/live-paper-bootstrap-status/` on cockpit load and manual refresh
- `POST /api/mission-control/bootstrap-live-paper-session/` from a single action button (`live_read_only_paper_conservative` preset by default)

The card shows current preset, session/heartbeat state, runtime/market/paper modes, compact bootstrap result summaries (`bootstrap_action`, `bootstrap_summary`, `next_step_summary`) and explicit guardrails:

- `REAL_READ_ONLY`
- `PAPER_ONLY`
- `live_execution_enabled = false`

Scope remains strictly operational + paper-only: no new screen, no wizard, no `/runtime` rewrite, and no live-trading enablement.

### Live Paper Autopilot operational snapshot (frontend, delta)

The same `/cockpit` **Live Paper Autopilot** card now adds a compact **Operational Snapshot** block (no new page) to answer if the loop is truly alive and progressing.

- Reuses existing endpoints only:
  - `GET /api/mission-control/live-paper-bootstrap-status/`
  - `GET /api/mission-control/autonomous-heartbeat-summary/`
  - `GET /api/mission-control/autonomous-heartbeat-runs/`
  - `GET /api/mission-control/live-paper-attention-alert-status/`
  - `POST /api/mission-control/sync-live-paper-attention-alert/` (manual fallback)
- Displays compact operational hints:
  - `session_active` / `heartbeat_active`
  - `current_session_status`
  - last heartbeat timestamps + latest heartbeat run outcome summary
  - `Operational attention` mini-block for heartbeat auto-sync availability/result, active alert state/severity, and `attention_mode`
  - funnel-aware operational attention context from the same bridge payload (no new endpoint): `funnel_status`, `stalled_stage`, `top_stage`, `funnel_summary`
    - compact badge: `ACTIVE` / `THIN_FLOW` / `STALLED`
    - short lines: `Stalled at: ...` or `Top stage: ...`
    - compact fallback when unavailable: `Funnel context unavailable`
  - explicit `Sync attention alert` button as manual fallback (with compact feedback + refresh)
  - `status_summary` from bootstrap status

This remains strictly `REAL_READ_ONLY` + `PAPER_ONLY`; it improves observability only (including “alive but unproductive” vs stalled funnel awareness) and does not enable live execution.

### Live Paper Autopilot Operational Attention Bridge (backend, new)

`mission_control` now includes a compact backend-only bridge that converts existing live-paper operational signals into one deduplicated `operator_alerts` signal to further reduce manual cockpit checking.

- service: `apps/backend/apps/mission_control/services/live_paper_attention_bridge.py`
- global dedupe key: `live_paper_autopilot_attention_global`
- API:
  - `POST /api/mission-control/sync-live-paper-attention-alert/`
  - `GET /api/mission-control/live-paper-attention-alert-status/`
- attention mode mapping (explicit + conservative):
  - `BLOCKED` → high active alert
  - `REVIEW_NOW` → high active alert
  - `DEGRADED` → warning active alert
  - `HEALTHY` → resolve bridge alert if present
- low-noise sync actions:
  - `CREATED` / `UPDATED` / `RESOLVED` / `NOOP`
  - updates only on material field changes (`attention_mode`, `attention_needed`, `alert_severity`, `current_session_status`, normalized `attention_reason_codes`)

This bridge reuses mission-control bootstrap/heartbeat/health/recovery summaries and existing `operator_alerts` services, introduces no new models, keeps paper-only scope, and does not change runtime/trading operation logic.

The bridge now also consumes the existing Live Paper Autonomy Funnel snapshot (`funnel_status`, `stalled_stage`, `top_stage`, `funnel_summary`) to detect “alive but unproductive” autopilot flow with low noise:
- `STALLED` + live session/heartbeat can escalate to `REVIEW_NOW`
- `THIN_FLOW` maps conservatively to `DEGRADED`
- strong operational `BLOCKED` signals still take precedence over funnel hints
- if funnel signal is unavailable, bridge falls back to existing logic with explicit `funnel_signal_unavailable` reason code

It now also auto-syncs once per local mission-control heartbeat pass (reusing the existing local loop; no new scheduler). Heartbeat summary exposes compact `live_paper_attention_sync` (`attempted`, `success`, `alert_action`, `attention_mode`, `session_active`, `heartbeat_active`, `current_session_status`, `sync_summary`), and manual `POST /api/mission-control/sync-live-paper-attention-alert/` remains intact as fallback.


### Live Paper V1 Smoke Test Runner (backend, new)

`mission_control` now exposes a compact backend-only smoke test runner that chains existing live-paper bootstrap + heartbeat + validation services for a short deterministic V1 check.

- service: `apps/backend/apps/mission_control/services/live_paper_smoke_test.py`
- API:
  - `POST /api/mission-control/run-live-paper-smoke-test/`
    - optional body: `preset` (default `live_read_only_paper_conservative`), `heartbeat_passes` (default `1`, max `2`)
  - `GET /api/mission-control/live-paper-smoke-test-status/`
- run order (reused components only):
  1. read validation digest (before)
  2. run/reuse live paper bootstrap session
  3. run 1–2 heartbeat passes
  4. read validation digest (after)
  5. emit compact `PASS` / `WARN` / `FAIL` result + deterministic checks summary

Scope remains unchanged: real-market read-only signals + paper-money-only execution (`REAL_READ_ONLY`, `PAPER_ONLY`), no live trading enablement, no new scheduler, and no new persistent models.

### Live Paper Smoke Test cockpit card (frontend, new)

`/cockpit` now includes a compact **Live Paper Smoke Test** card near existing live-paper cards for quick V1 verification without creating a new screen.

- consumes existing backend endpoints:
  - `GET /api/mission-control/live-paper-smoke-test-status/` on cockpit load and manual refresh
  - `POST /api/mission-control/run-live-paper-smoke-test/` from a single action button
- default run payload sent by UI:
  - `preset = live_read_only_paper_conservative`
  - `heartbeat_passes = 1`
- compact card output:
  - strong `PASS` / `WARN` / `FAIL` badge
  - `smoke_test_summary` + `next_action_hint`
  - validation before/after and heartbeat completed counters
  - `recent_activity_detected` + `recent_trades_detected`
  - compact checks list (`check_name`, status, summary) from the most recent run executed in cockpit
- compact actions:
  - `Run smoke test`
  - `Refresh smoke result`

Fallback behavior is explicit and non-breaking: if no run exists yet it shows `No smoke test result yet`; on endpoint errors it shows `Live paper smoke test unavailable`.

Scope remains strictly real-market read-only + fake-money paper execution and does not enable live trading.

### Live Paper Trial Run cockpit card (frontend, new)

`/cockpit` now includes a compact **Live Paper Trial Run** card for a one-click short V1 paper verification flow (no new screen).

- The card is now backend-driven and consumes only:
  - `POST /api/mission-control/run-live-paper-trial/`
  - `GET /api/mission-control/live-paper-trial-status/`
- `Run trial` calls the compact backend endpoint and uses its response as the source of truth.
- `Refresh trial status` only re-reads latest trial status (no frontend re-orchestration).
- On cockpit load, status is read from backend and a compact `No trial run yet` fallback is shown on 404.
- compact card output:
  - `trial_status`: `PASS` / `WARN` / `FAIL` (backend-classified)
  - `trial_summary`, `next_action_hint`, smoke/validation status, heartbeat passes
  - when available from run response: `bootstrap_action`, validation before/after, activity/trade/snapshot flags, and compact checks

Scope remains unchanged: `REAL_READ_ONLY` + `PAPER_ONLY`, no `/runtime` changes, no scheduler additions, no live trading enablement, and no parallel trial orchestration logic in frontend.

### Test Console cockpit card (frontend, new)

`/cockpit` now includes a compact **Test Console** panel that centralizes the V1 paper operational flow in one place (without creating a new page).

- backend endpoints used by frontend:
  - `POST /api/mission-control/test-console/start/`
  - `POST /api/mission-control/test-console/stop/`
  - `GET /api/mission-control/test-console/status/`
  - `GET /api/mission-control/test-console/export-log/?format=text`
- operator actions in a single card:
  - `Start test`
  - `Stop test`
  - `Refresh status`
  - `Export log`
  - `Copy log`
- status summary shown in-card:
  - `test_status`, `current_phase`, `started_at`, `ended_at`
  - validation/trial/trend/readiness/gate/extended-run/attention/funnel
  - compact `scan_summary`, `portfolio_summary`, `next_action_hint`, optional `blocker_summary`
  - `portfolio_summary` includes compact account diagnostics: `account_summary_status` (`PAPER_ACCOUNT_SUMMARY_OK` / `PAPER_ACCOUNT_SUMMARY_DEGRADED` / `PAPER_ACCOUNT_SUMMARY_UNAVAILABLE`) plus `account_summary_reason_codes`
- compact log pane:
  - log text is rendered directly in the card for easy copy/paste into chat
  - fallback: `No log exported yet`
  - export failure fallback: `Unable to export test log`
  - status failure fallback: `Test Console unavailable`

Scope and safety remain unchanged: strictly `REAL_READ_ONLY` + `PAPER_ONLY`; this does **not** enable live trading.

Cockpit also includes a compact **Live Paper Trial History** card that consumes:
- `GET /api/mission-control/live-paper-trial-history/?limit=5`
- manual action: `Refresh history`
- automatic refresh right after `Run trial` completes

Cockpit now also includes a compact **Trial Trend** card that consumes:
- `GET /api/mission-control/live-paper-trial-trend/?limit=5`
- manual action: `Refresh trend`
- automatic refresh on cockpit load and immediately after `Run trial`

The card adds deterministic trend/readiness signals over recent trial history:
- trend: `IMPROVING` / `STABLE` / `DEGRADING` / `INSUFFICIENT_DATA`
- readiness: `READY_FOR_EXTENDED_RUN` / `NEEDS_REVIEW` / `NOT_READY`
- compact digest: summary, next action hint, PASS/WARN/FAIL counts, and recent statuses line

This remains operational-only aggregation for paper runs and keeps strict `REAL_READ_ONLY` + `PAPER_ONLY` scope.

Cockpit now also includes a compact **Extended Run Gate** card that consumes:
- `GET /api/mission-control/extended-paper-run-gate/`
- manual action: `Refresh gate`
- automatic refresh on cockpit load, and after `Run trial`, `Refresh trend`, and `Refresh validation`

The card provides a concise operational decision for a longer paper run:
- strong `gate_status` badge (`ALLOW` / `ALLOW_WITH_CAUTION` / `BLOCK`)
- `gate_summary` + `next_action_hint`
- compact status line for `latest_trial_status`, `trend_status`, `readiness_status`, `validation_status`, `attention_mode`, `funnel_status`
- compact checks (`PASS` / `WARN` / `FAIL`) and readable `reason_codes` (when available)

This remains read-only/paper-only (`REAL_READ_ONLY` + `PAPER_ONLY`), complements existing cockpit cards, and does not enable live trading.

Cockpit now also includes a compact **Extended Paper Run** card that consumes:
- `POST /api/mission-control/start-extended-paper-run/`
- `GET /api/mission-control/extended-paper-run-status/`
- manual actions:
  - `Start extended run`
  - `Refresh extended status`

The card is intentionally compact and operational:
- primary status badge from `launch_status` (`STARTED` / `REUSED_RUNNING_SESSION` / `REUSED_PAUSED_SESSION` / `BLOCKED` / `FAILED`)
- fallback badge from `gate_status` when no launch has been requested yet
- concise `launch_summary` or `status_summary`, plus `next_action_hint`
- short state line for `gate_status`, `session_active`, `heartbeat_active`, `current_session_status`, `caution_mode`, `extended_run_active`
- compact readable `reason_codes` when available

Scope remains unchanged: `REAL_READ_ONLY` + `PAPER_ONLY`; no new screen, no `/runtime` changes, no new polling/websocket loop, and no live trading enablement.

### Extended Paper Run Launcher (backend, new)

`mission_control` now exposes a compact backend launcher for extended paper runs guarded directly by the existing Extended Paper Run Gate decision.

- service: `apps/backend/apps/mission_control/services/extended_paper_run_launcher.py`
- endpoints:
  - `POST /api/mission-control/start-extended-paper-run/`
    - optional body: `preset` (default `live_read_only_paper_conservative`)
  - `GET /api/mission-control/extended-paper-run-status/`
- guardrail behavior:
  - gate `BLOCK` => launch denied (`launch_status=BLOCKED`)
  - gate `ALLOW` => normal start/reuse (`caution_mode=false`)
  - gate `ALLOW_WITH_CAUTION` => cautious start/reuse (`caution_mode=true`)
- reuses existing live-paper bootstrap/session/heartbeat stack (no new scheduler, no parallel authority).
- boundaries remain strict:
  - real market data read-only (`REAL_READ_ONLY`)
  - execution paper-only (`PAPER_ONLY`)
  - no live trading enablement.

### Live Paper Trial Run History (backend, new)

`mission_control` now keeps a compact in-memory history of recent Live Paper Trial runs for quick operational comparison across the latest V1 paper checks.

- service: `apps/backend/apps/mission_control/services/live_paper_trial_history.py`
- API:
  - `GET /api/mission-control/live-paper-trial-history/`
  - optional query params:
    - `limit` (default `5`, max `20`)
    - `status` (`PASS` | `WARN` | `FAIL`)
- behavior:
  - auto-records each successful `POST /api/mission-control/run-live-paper-trial/` result
  - keeps newest-first bounded buffer in memory (no DB model/migration)
  - returns compact payload: `count`, `latest_trial_status`, deterministic `history_summary`, and `items`

This is operational evidence only for recent paper runs, remains strictly `REAL_READ_ONLY` + `PAPER_ONLY`, and does not enable live trading.

### Live Paper Trial Trend Digest (backend + cockpit, new)

`mission_control` now exposes a compact trend/readiness digest over the existing recent trial history to answer quickly whether V1 paper checks are improving, stable, degrading, or insufficient.

- service: `apps/backend/apps/mission_control/services/live_paper_trial_trend.py`
- API:
  - `GET /api/mission-control/live-paper-trial-trend/`
  - query params:
    - `limit` (optional, default `5`, max `20`)
    - `preset` (optional, filters the sampled history items)
- payload:
  - `sample_size`
  - `latest_trial_status`
  - `latest_validation_status`
  - `trend_status`
  - `readiness_status`
  - `trend_summary`
  - `next_action_hint`
  - `counts` (`pass_count`, `warn_count`, `fail_count`)
  - optional `recent_statuses`

This layer is deterministic and explainable, reuses live-paper trial history as its source, adds no new screen/analytics architecture, and remains strictly `REAL_READ_ONLY` + `PAPER_ONLY`.

### Live Paper Autonomy Funnel Snapshot (backend + cockpit, new)

`mission_control` now includes a compact **Live Paper Autonomy Funnel Snapshot** to validate if autonomy is truly advancing through scan → research → prediction → risk → paper execution in a recent window.

- backend service: `apps/backend/apps/mission_control/services/live_paper_autonomy_funnel.py`
- API:
  - `GET /api/mission-control/live-paper-autonomy-funnel/`
  - query params:
    - `window_minutes` (default `60`)
    - `preset` (default `live_read_only_paper_conservative`)
- compact digest payload includes:
  - `funnel_status`: `ACTIVE` / `THIN_FLOW` / `STALLED`
  - stage counts + `top_stage` + optional `stalled_stage`
  - deterministic `next_action_hint` + `funnel_summary`
  - compact `stages` list (`scan`, `research`, `prediction`, `risk`, `paper_execution`) with `ACTIVE` / `LOW` / `EMPTY`

Cockpit now renders a sister card **Autonomy Funnel** (near Live Paper Validation + Smoke Test) with:
- strong status badge (`ACTIVE` / `THIN_FLOW` / `STALLED`)
- short summary + deterministic hint
- compact per-stage counts and status badges
- non-blocking fallback: `Autonomy funnel unavailable`
- manual action: `Refresh funnel`

This remains strictly real-market read-only + paper-money-only execution, introduces no new persistent models, no scheduler/polling/websocket changes, no `/runtime` changes, and no live trading enablement.

### Extended Paper Run Gate (backend, new)

`mission_control` now includes a compact backend-only **Extended Paper Run Gate** that aggregates existing live-paper signals and returns a deterministic decision on whether a longer paper run should start.

- backend service: `apps/backend/apps/mission_control/services/extended_paper_run_gate.py`
- API:
  - `GET /api/mission-control/extended-paper-run-gate/`
  - optional query param: `preset` (default `live_read_only_paper_conservative`)
- gate statuses:
  - `ALLOW`
  - `ALLOW_WITH_CAUTION`
  - `BLOCK`
- reused inputs:
  - Live Paper Validation Digest
  - Live Paper Trial Trend Digest + Trial History
  - Live Paper Operational Attention status
  - Live Paper Autonomy Funnel snapshot
  - Live Paper bootstrap/status context
- compact explainable output:
  - `gate_status`, `next_action_hint`, `gate_summary`
  - status fields (`validation_status`, `readiness_status`, `latest_trial_status`, `trend_status`, `attention_mode`, `funnel_status`)
  - `reason_codes`
  - compact `checks` (`validation`, `trial_trend`, `operational_attention`, `autonomy_funnel`, `recent_trial_quality`)

This gate is read-only and explainable by design: it adds no new persistent models, no mutative endpoint, no scheduler changes, does not enable live trading, and remains strictly `REAL_READ_ONLY` + `PAPER_ONLY`.

### Live Paper V1 Validation Digest (backend, new)

`mission_control` now includes a compact read-only validation digest that answers, in one backend response, whether the live read-only paper V1 loop is operational right now.

- service: `apps/backend/apps/mission_control/services/live_paper_validation.py`
- API:
  - `GET /api/mission-control/live-paper-validation/`
  - optional query param: `preset` (default: `live_read_only_paper_conservative`)
- deterministic statuses:
  - `READY`: session + heartbeat active, non-blocking attention, account/economic snapshot available, and useful recent evidence
  - `WARNING`: loop is alive but missing key evidence (e.g., no recent trades/activity yet, partial snapshot, degraded attention)
  - `BLOCKED`: session/heartbeat down, blocking attention mode, or missing minimum paper account/economic readiness

The digest is strictly an aggregation/validation layer: it reuses existing bootstrap/heartbeat/attention/paper signals, introduces no new models, and remains real-market read-only plus paper-money-only execution.

### Live Paper Validation cockpit card (frontend, new)

`/cockpit` now includes a compact **Live Paper Validation** card next to the existing live-paper operational cards.

- consumes existing backend digest endpoint:
  - `GET /api/mission-control/live-paper-validation/`
- shows at-a-glance V1 readiness:
  - strong status badge: `READY` / `WARNING` / `BLOCKED`
  - `validation_summary` + `next_action_hint`
  - compact state line for `session_active`, `heartbeat_active`, `attention_mode`, `paper_account_ready`, `portfolio_snapshot_ready`
  - short check list (`PASS` / `WARN` / `FAIL`)
- includes compact actions:
  - `Refresh validation`
  - optional navigation shortcut to autopilot (`Open autopilot`)

The card complements (does not replace) **Live Paper Autopilot**, **Operational Snapshot**, and **Paper Portfolio Snapshot** and remains strictly `REAL_READ_ONLY` + `PAPER_ONLY` (no live trading enablement).

### Runtime Tuning Review Escalation (new)

`runtime_governor` now exposes a compact read-only **Runtime Tuning Review Escalation** layer above existing tuning review queue + aging.

- API:
  - `GET /api/runtime-governor/tuning-review-escalation/`
  - `GET /api/runtime-governor/tuning-review-escalation/<source_scope>/`
- optional list query params:
  - `escalated_only` (default `true`)
  - `escalation_level` (`MONITOR` | `ELEVATED` | `URGENT`)
  - `limit` (default compact list)
- deterministic escalation levels:
  - `URGENT`: overdue follow-up/stale items, or overdue unreviewed + `REVIEW_NOW`
  - `ELEVATED`: aging follow-up/stale items, overdue unreviewed, or aging unreviewed with high technical priority
  - `MONITOR`: remaining unresolved items

This layer is paper-only/read-only and does not change runtime operation logic, manual-review actions, or `/runtime` authority paths. Cockpit uses it as a compact prioritization strip above existing review aging + review queue.

### Runtime Tuning Review Activity Feed (new)

`runtime_governor` now exposes a compact read-only **Runtime Tuning Review Activity Feed** derived directly from existing manual review actions (`RuntimeTuningReviewAction`).

- API:
  - `GET /api/runtime-governor/tuning-review-activity/`
  - `GET /api/runtime-governor/tuning-review-activity/<source_scope>/`
- optional list query params:
  - `source_scope`
  - `action_type` (`ACKNOWLEDGE_CURRENT` | `MARK_FOLLOWUP_REQUIRED` | `CLEAR_REVIEW_STATE`)
  - `limit` (compact default: `10`)
- payload focus:
  - deterministic `activity_summary`
  - compact action labels (`ACKNOWLEDGED`, `FOLLOWUP_MARKED`, `REVIEW_CLEARED`)
  - explicit reason codes (action + resulting state)
  - scope review summary + runtime investigation deep links

Cockpit uses this as recent human-context next to queue/aging/escalation so operators can see what manual actions happened recently before a scope becomes stale or urgent. This remains paper-only/read-only and does not change runtime tuning operation logic.

### Runtime Tuning Autotriage Alert Bridge (new)

`runtime_governor` now includes a compact **Runtime Tuning Autotriage Alert Bridge** that maps existing autotriage output into a single deduplicated operational alert signal.

- global dedupe key: `runtime_tuning_autotriage_global`
- API:
  - `POST /api/runtime-governor/sync-tuning-autotriage-alert/`
  - `GET /api/runtime-governor/tuning-autotriage-alert-status/`
  - `GET /api/mission-control/autonomous-heartbeat-summary/` now includes compact `runtime_tuning_attention_sync`
- mapping:
  - `REVIEW_NOW` → active runtime operator alert (`high`)
  - `REVIEW_SOON` → active runtime operator alert (`warning`)
  - `MONITOR_ONLY` / `NO_ACTION` → resolve existing bridge alert

The bridge now also auto-syncs once per local heartbeat pass (reusing the existing mission-control heartbeat loop; no new scheduler). Manual sync remains available as fallback. This complements existing autotriage/queue/aging/escalation flows, reduces manual cockpit-only dependency, keeps full alert history, and remains paper-only with no runtime execution logic changes.

It now includes **Runtime Tuning Alert Low-Noise Stabilization**: the bridge only updates active alerts on material signal changes (`human_attention_mode`, `alert_needed`, `alert_severity`, `next_recommended_scope`, normalized `next_recommended_reason_codes`, `requires_human_now`). Repeated heartbeat syncs on equivalent state return `NOOP` with suppression metadata instead of noisy `UPDATED` churn.

### Governance review queue (new)

`mission_control` now includes a **unified governance review queue** to centralize pending manual triage from:

- `runtime_governor` (`runtime_feedback_apply`, `mode_stabilization`)
- `mission_control` (`session_health`, `session_recovery`, `session_admission`)
- `portfolio_governor` (`exposure_coordination`, `exposure_apply`)

Flow:

`blocked/manual/deferred/advisory outcomes -> unified queue -> severity + priority + recommendations -> operator inbox`

Scope and boundaries:

- paper-only and local-first
- no live trading / no real money
- no replacement of existing authorities
- no LLM as final authority

### Governance review manual-safe resolution (new)

`mission_control` now closes the governance loop with explicit operator-driven resolution:

`review item -> operator resolution -> safe manual action -> auditable resolution record`

- new entity: `GovernanceReviewResolution`
- new actions:
  - `APPLY_MANUAL_APPROVAL`
  - `KEEP_BLOCKED`
  - `DISMISS_AS_EXPECTED`
  - `REQUIRE_FOLLOWUP`
  - `RETRY_SAFE_APPLY`
- API:
  - `POST /api/mission-control/resolve-governance-review-item/<item_id>/`
  - `GET /api/mission-control/governance-review-resolutions/`

Boundaries stay strict: paper-only, no real money/live execution, and no replacement of runtime/safety/portfolio/mission authorities.

### Governance auto-resolution (low-risk only) (new)

`mission_control` now adds a **small conservative auto-resolution layer** on top of the existing governance review queue and manual-safe resolution path:

`open governance items -> explicit low-risk eligibility -> auto-dismiss / safe retry / follow-up deferral -> audit trail`

- new entities:
  - `GovernanceAutoResolutionRun`
  - `GovernanceAutoResolutionDecision`
  - `GovernanceAutoResolutionRecord`
- API:
  - `POST /api/mission-control/run-governance-auto-resolution/`
  - `GET /api/mission-control/governance-auto-resolution-runs/`
  - `GET /api/mission-control/governance-auto-resolution-decisions/`
  - `GET /api/mission-control/governance-auto-resolution-records/`
  - `GET /api/mission-control/governance-auto-resolution-summary/`
  - optional manual replay: `POST /api/mission-control/apply-governance-auto-resolution/<decision_id>/`

Guardrails:
- only explicit low-risk paths are auto-applied
- no high/critical ambiguous auto-resolution
- no incident/safety/runtime-pressure auto-resolution
- no replacement of manual governance resolution authority
- paper-only scope, no live trading, no real money

### Governance queue aging & escalation (new)

`mission_control` now includes an explicit **queue aging/escalation pass** focused only on stale governance backlog pressure:

`open governance items -> age/staleness review -> overdue escalation -> updated priority/recommendation -> audit trail`

- new entities:
  - `GovernanceQueueAgingRun`
  - `GovernanceQueueAgingReview`
  - `GovernanceQueueAgingRecommendation`
- API:
  - `POST /api/mission-control/run-governance-queue-aging-review/`
  - `GET /api/mission-control/governance-queue-aging-runs/`
  - `GET /api/mission-control/governance-queue-aging-reviews/`
  - `GET /api/mission-control/governance-queue-aging-recommendations/`
  - `GET /api/mission-control/governance-queue-aging-summary/`

Guardrails:
- does not auto-resolve items (review/escalation only)
- does not replace the existing governance queue or low-risk auto-resolution
- paper-only scope (no live trading / no real money)
- reduces risk of human-review backlog drift and hidden stale blockers
- explicit rules cover: old `OPEN` escalation, stalled `IN_REVIEW` overdue, follow-up due now, and persistent blocked stale escalation

### Governance backlog pressure (delta-only) (new)

`mission_control` now includes a compact and auditable **governance backlog pressure** layer that turns current human backlog status into an additional conservative runtime signal:

`open governance backlog + aging outcomes -> pressure snapshot -> pressure decision -> conservative recommendation`

- new entities:
  - `GovernanceBacklogPressureRun`
  - `GovernanceBacklogPressureSnapshot`
  - `GovernanceBacklogPressureDecision`
  - `GovernanceBacklogPressureRecommendation`
- API:
  - `POST /api/mission-control/run-governance-backlog-pressure-review/`
  - `GET /api/mission-control/governance-backlog-pressure-runs/`
  - `GET /api/mission-control/governance-backlog-pressure-snapshots/`
  - `GET /api/mission-control/governance-backlog-pressure-decisions/`
  - `GET /api/mission-control/governance-backlog-pressure-recommendations/`
  - `GET /api/mission-control/governance-backlog-pressure-summary/`

Guardrails:
- does not replace governance review queue, auto-resolution, or queue aging/escalation
- only adds an extra conservative runtime signal (`governance_backlog_pressure_state`)
- paper-only scope (no live trading / no real money)

### Global operating mode downstream enforcement bridge (new)

`runtime_governor` now includes an explicit and auditable **downstream mode enforcement bridge**:

- `global operating mode -> enforcement rules -> module impacts -> enforcement decisions -> recommendations`
- coverage across:
  - session timing policy
  - session admission capacity
  - portfolio exposure coordination/apply
  - autonomous execution intake
  - heartbeat runner cadence
  - session recovery/resume conservatism
- API:
  - `POST /api/runtime-governor/run-mode-enforcement-review/`
  - `GET /api/runtime-governor/mode-enforcement-runs/`
  - `GET /api/runtime-governor/mode-module-impacts/`
  - `GET /api/runtime-governor/mode-enforcement-decisions/`
  - `GET /api/runtime-governor/mode-enforcement-recommendations/`
  - `GET /api/runtime-governor/mode-enforcement-summary/`

This bridge does not replace runtime/safety/portfolio/mission authorities; it adds a coherent global-mode bias layer above them. Scope remains local-first, single-user, paper/sandbox only, no real-money/live execution.

### Runtime performance feedback controller / regime self-assessment (new)

`runtime_governor` now adds an explicit, auditable, and conservative runtime self-assessment layer:

- flow:
  - recent runtime behavior
  - aggregate `RuntimePerformanceSnapshot`
  - `RuntimeDiagnosticReview`
  - `RuntimeFeedbackDecision`
  - `RuntimeFeedbackRecommendation`
- key entities:
  - `RuntimeFeedbackRun`
  - `RuntimePerformanceSnapshot`
  - `RuntimeDiagnosticReview`
  - `RuntimeFeedbackDecision`
  - `RuntimeFeedbackRecommendation`
- API:
  - `POST /api/runtime-governor/run-runtime-feedback-review/`
  - `GET /api/runtime-governor/runtime-feedback-runs/`
  - `GET /api/runtime-governor/runtime-performance-snapshots/`
  - `GET /api/runtime-governor/runtime-diagnostic-reviews/`
  - `GET /api/runtime-governor/runtime-feedback-decisions/`
  - `GET /api/runtime-governor/runtime-feedback-recommendations/`
  - `GET /api/runtime-governor/runtime-feedback-summary/`
  - `POST /api/runtime-governor/apply-runtime-feedback-decision/<decision_id>/`

This layer provides conservative global tuning input and traceability; it does not replace runtime_governor, mission_control, portfolio_governor, risk, safety, or incident authorities. Scope remains local-first, single-user, paper-only, and no live execution.

Backlog-pressure integration was tightened in this delta:
- runtime feedback performance snapshots now persist `governance_backlog_pressure_state`
- diagnostics and feedback decisions now add explicit reason codes/summaries for `CAUTION` / `HIGH` / `CRITICAL`
- `HIGH`/`CRITICAL` now apply stricter relax gating and stronger manual-review bias
- `CRITICAL` can bias toward monitor-only when other runtime signals are not severe
- `NORMAL` keeps base behavior

This remains conservative, transparent, paper-only, and does not replace existing authorities.

Runtime conservative tuning is now centralized in `apps/backend/apps/runtime_governor/tuning_profiles.py` so backlog-pressure thresholds/weights and backlog-driven relax/manual-review/monitor-only biases are explicit and adjustable without redesign. Default behavior remains conservative and paper-only; this is tuning readability, not live-trading scope expansion.

Runtime governor now also exposes a read-only active tuning observability layer so operators can audit the currently active profile and its effective runtime-facing guardrails:
- `GET /api/runtime-governor/tuning-profile-summary/`
- `GET /api/runtime-governor/tuning-profile-values/`

This layer is visibility-only (no CRUD, no edit path), remains paper-only, and does not change runtime behavior by itself.

Runtime governor summaries now also propagate the active tuning context directly in:
- `GET /api/runtime-governor/runtime-feedback-summary/`
- `GET /api/runtime-governor/operating-mode-summary/`
- `GET /api/runtime-governor/mode-stabilization-summary/`
- `GET /api/runtime-governor/mode-enforcement-summary/`

Added fields are traceability-only (`tuning_profile_name`, `tuning_effective_values`, `tuning_guardrail_summary`, plus profile summary/fingerprint metadata) so operators can audit what tuning influenced each cross-layer summary. This does not alter decision logic, remains paper-only, and improves debugging/auditability.

Runtime governor now also persists a lightweight tuning-context history for temporal auditability:
- `RuntimeTuningContextSnapshot` records per-scope snapshots (`runtime_feedback`, `operating_mode`, `mode_stabilization`, `mode_enforcement`) with run-id linkage, fingerprint, profile name, and drift annotation.
- drift rules are explicit: `INITIAL`, `NO_CHANGE`, `MINOR_CONTEXT_CHANGE`, `PROFILE_CHANGE`.
- API:
  - `GET /api/runtime-governor/tuning-context-snapshots/`
  - `GET /api/runtime-governor/tuning-context-drift-summary/`
  - `GET /api/runtime-governor/tuning-context-diffs/`
    - query (read-only observability): `source_scope`, `drift_status`, `latest_only`, `limit`, optional `created_after` / `created_before`
  - `GET /api/runtime-governor/tuning-context-snapshots/`
    - query (read-only observability): `source_scope`, `latest_only`, `limit`

This history layer is observability-only, keeps paper-only boundaries, does not enable live trading/real money, and does not change operational decisions.

On top of that observability, runtime governor now exposes a compact read-only tuning change alert signal per scope:
- `GET /api/runtime-governor/tuning-change-alerts/` (`source_scope` optional).
- Alert states are transparent and non-operational: `STABLE`, `MINOR_CHANGE`, `PROFILE_SHIFT`, `REVIEW_NOW`.
- Rule mapping remains explicit (`NO_CHANGE` → `STABLE`, `MINOR_CONTEXT_CHANGE` → `MINOR_CHANGE`, `PROFILE_CHANGE` → `PROFILE_SHIFT`) with `REVIEW_NOW` escalation when relevant changes are broad or a recent profile shift exists.

This addition is summary-only for faster technical review; it does not auto-apply changes and does not alter runtime behavior.

Runtime governor now also exposes a **Cockpit Runtime Tuning Attention Panel** handoff so `/cockpit` can surface only the highest-signal tuning scopes without reimplementing runtime semantics:
- `GET /api/runtime-governor/tuning-cockpit-panel/`
- `GET /api/runtime-governor/tuning-cockpit-panel/<source_scope>/`
- optional query params: `attention_only` (default `true`), `limit` (default `5`), `source_scope`
- payload includes deep-link handoff (`/runtime?tuningScope=<scope>`), priority/rank, alert+drift status, compact diff/correlation context, and quick-view detail fields.

This remains read-only, paper-only, and decision-neutral: cockpit consumes/summarizes runtime-governor review-board output but does not change operational logic or replace existing attention/operator queues.

Cockpit now also supports an inline compact `Investigate` drill-down per scope by reusing `GET /api/runtime-governor/tuning-investigation/<source_scope>/` directly inside **Runtime Tuning Attention**, with a clear handoff button to `/runtime?tuningScope=<scope>&investigate=1` for the full investigation workflow. This remains read-only/paper-only and does not introduce operational mutations.

### Runtime feedback apply bridge / closed-loop tuning (new)

`runtime_governor` now closes the loop from runtime feedback into conservative global posture adjustment:

- flow:
  - `RuntimeFeedbackDecision`
  - `RuntimeFeedbackApplyDecision`
  - `RuntimeFeedbackApplyRecord`
  - optional global operating mode switch
  - optional downstream mode enforcement refresh
- auditable entities:
  - `RuntimeFeedbackApplyRun`
  - `RuntimeFeedbackApplyDecision`
  - `RuntimeFeedbackApplyRecord`
  - `RuntimeFeedbackApplyRecommendation`
- API:
  - `POST /api/runtime-governor/run-runtime-feedback-apply-review/`
  - `POST /api/runtime-governor/apply-runtime-feedback-decision/<decision_id>/`
  - `GET /api/runtime-governor/runtime-feedback-apply-runs/`
  - `GET /api/runtime-governor/runtime-feedback-apply-decisions/`
  - `GET /api/runtime-governor/runtime-feedback-apply-records/`
  - `GET /api/runtime-governor/runtime-feedback-apply-recommendations/`
  - `GET /api/runtime-governor/runtime-feedback-apply-summary/`

The bridge is conservative and transparent (manual-review blocks, safety-aware apply rules, hysteresis-friendly behavior). It does not replace existing authorities and remains local-first, single-user, paper/sandbox only, no real money, and no live broker/exchange execution.

### Runtime mode stabilization review layer (new)

`runtime_governor` now includes a dedicated stabilization review path for global mode transition intents:

- flow:
  - mode change intent
  - `RuntimeModeTransitionSnapshot`
  - `RuntimeModeStabilityReview`
  - `RuntimeModeTransitionDecision`
  - `RuntimeModeStabilizationRecommendation`
- run-level audit entity:
  - `RuntimeModeStabilizationRun`
- API:
  - `POST /api/runtime-governor/run-mode-stabilization-review/`
  - `GET /api/runtime-governor/mode-stabilization-runs/`
  - `GET /api/runtime-governor/mode-transition-snapshots/`
  - `GET /api/runtime-governor/mode-stability-reviews/`
  - `GET /api/runtime-governor/mode-transition-decisions/`
  - `GET /api/runtime-governor/mode-stabilization-recommendations/`
  - `GET /api/runtime-governor/mode-stabilization-summary/`

This layer is transparent and paper-only. It now supports stabilized transition apply records (`RuntimeModeTransitionApplyRecord`), manual apply via API, optional conservative `auto_apply_safe`, and enforcement refresh only when the global mode actually changes. It complements operating mode + runtime feedback apply + downstream enforcement and does **not** replace those existing authorities.

### Precedent-aware agents (new)

- Memory is now used as **decision support**, not as an opaque planner.
- Core sequence:
  1) retrieval (`MemoryRetrievalRun` + `RetrievedPrecedent`)
  2) precedent summary (`top similar cases`, `failure modes`, `lessons`)
  3) conservative influence suggestion (`context_only`, `caution_boost`, `confidence_adjust`, `rationale_only`)
  4) auditable use record (`AgentPrecedentUse`)
- Influence is bounded: it can add caution/reduce confidence/rationale, but it does **not** replace core numeric policy/risk/safety gates.
- Still local-first, single-user, and paper/demo only.

### Real data UX boundary (current)


### Paper trading on real-market data (current)

The backend now supports **paper trading using real read-only market data**:

- real market data can be ingested and used as paper pricing reference
- execution still stays `paper_demo_only` with fictional cash/positions/trades
- risk/policy/proposal flows can evaluate trades on real read-only markets
- serializers expose explicit source/execution context for frontend clarity

Still not implemented: real auth, real order placement, real portfolio sync, or real execution paths.


- Frontend markets views now distinguish **demo/local** markets from **real/read-only** markets with explicit source badges and filters.
- Frontend now also surfaces **paper-tradable vs blocked** status (with backend reason) for real read-only markets in `/markets` and `/markets/:marketId`.
- Real provider data is explorable in `/markets` and `/markets/:marketId` as read-only context.
- Paper trading remains simulated only; no real execution path is enabled from the frontend.

### Semi-autonomous demo mode (current)

The platform now includes a conservative semi-autonomous demo mode:

- evaluate-only proposal classification
- guarded paper-only auto execution for strict AUTO_APPROVE cases
- manual pending approval queue for APPROVAL_REQUIRED outcomes
- explicit hard blocks for policy HARD_BLOCK and safety guardrail failures

Still out of scope: real trading, exchange auth, autonomous schedulers/workers, websockets, and ML/LLM execution.

### Autonomous continuous demo loop (new)

### Autonomous session controller / cadence-aware mission runtime (new)

`mission_control` now includes a persistent autonomous session layer on top of existing autonomous runtime cycles:

- explicit session lifecycle (`RUNNING`, `PAUSED`, `STOPPED`, `DEGRADED`, `BLOCKED`, `COMPLETED`)
- cadence-aware tick orchestration with transparent decisions (`RUN_NOW`, `WAIT_SHORT/LONG`, `MONITOR_ONLY_NEXT`, `PAUSE_SESSION`, `STOP_SESSION`)
- auditable tick records linking session -> cadence decision -> runtime run -> cycle plan/execution/outcome
- explicit conservative recommendations for next-step governance
- manual controls to start, pause, resume, stop session, and run tick on demand

Boundaries remain strict: local-first, single-user, paper/sandbox only, no broker/exchange live execution, no real money, and no black-box scheduler authority.

### Local autonomous heartbeat runner / due-tick executor (new)

`mission_control` now includes a local self-advancing heartbeat runner layer for autonomous sessions:

- runner lifecycle endpoints (`start/pause/resume/stop-autonomous-runner`)
- heartbeat pass endpoint (`run-autonomous-heartbeat`) for explicit/manual trigger and local loop reuse
- auditable entities:
  - `AutonomousRunnerState`
  - `AutonomousHeartbeatRun`
  - `AutonomousHeartbeatDecision`
  - `AutonomousTickDispatchAttempt`
  - `AutonomousHeartbeatRecommendation`
- due-tick execution reuses existing `run-autonomous-tick` logic (no duplicate runtime authority)
- cooldown-aware, safety/runtime capability aware, and reentrancy-safe dispatch gating

Scope remains unchanged: local-first, single-user, paper/sandbox only, no live broker/exchange execution, and no real money.

### Autonomous session health monitor / anomaly escalation / self-healing governance (new)

`mission_control` now includes an explicit **session health governance layer** that sits on top of existing session control, timing policy, and heartbeat runner:

- pipeline: `session -> health snapshot -> anomaly -> intervention decision -> recommendation -> optional conservative apply`
- auditable entities:
  - `AutonomousSessionHealthRun`
  - `AutonomousSessionHealthSnapshot`
  - `AutonomousSessionAnomaly`
  - `AutonomousSessionInterventionDecision`
  - `AutonomousSessionInterventionRecord`
  - `AutonomousSessionHealthRecommendation`
- conservative intervention outcomes:
  - `KEEP_RUNNING`
  - `PAUSE_SESSION`
  - `RESUME_SESSION`
  - `STOP_SESSION`
  - `REQUIRE_MANUAL_REVIEW`
  - `ESCALATE_TO_INCIDENT_REVIEW`
- transparent API:
  - `POST /api/mission-control/run-session-health-review/`
  - `GET /api/mission-control/session-health-runs/`
  - `GET /api/mission-control/session-health-snapshots/`
  - `GET /api/mission-control/session-anomalies/`
  - `GET /api/mission-control/session-intervention-decisions/`
  - `GET /api/mission-control/session-health-recommendations/`
  - `GET /api/mission-control/session-health-summary/`

Boundaries remain strict: local-first, single-user, paper/sandbox only, no real money, no live broker/exchange routing, and no replacement of runtime/safety/incident/portfolio authorities.

### Autonomous session recovery review / stabilization eligibility (new)

`mission_control` now adds a conservative **recovery review layer** on top of session health governance:

- pipeline: paused/degraded/blocked session → recovery snapshot → blockers → resume decision → recommendation
- auditable entities:
  - `AutonomousSessionRecoveryRun`
  - `AutonomousSessionRecoverySnapshot`
  - `AutonomousRecoveryBlocker`
  - `AutonomousResumeDecision`
  - `AutonomousSessionRecoveryRecommendation`
- decisions are explicit and non-opaque:
  - `KEEP_PAUSED`
  - `READY_TO_RESUME`
  - `RESUME_IN_MONITOR_ONLY_MODE`
  - `REQUIRE_MANUAL_RECOVERY_REVIEW`
  - `STOP_SESSION_PERMANENTLY`
  - `ESCALATE_TO_INCIDENT_REVIEW`
- API:
  - `POST /api/mission-control/run-session-recovery-review/`
  - `GET /api/mission-control/session-recovery-runs/`
  - `GET /api/mission-control/session-recovery-snapshots/`
  - `GET /api/mission-control/session-recovery-blockers/`
  - `GET /api/mission-control/session-resume-decisions/`
  - `GET /api/mission-control/session-resume-records/`
  - `POST /api/mission-control/apply-session-resume/<decision_id>/`
  - `GET /api/mission-control/session-recovery-recommendations/`
  - `GET /api/mission-control/session-recovery-summary/`
  - `run-session-recovery-review` now accepts optional `auto_apply_safe` (default `false`) and only auto-applies `READY_TO_RESUME` + `auto_applicable=true`.

Resume apply remains conservative: blockers block apply, monitor-only decisions can be applied in `MONITOR_ONLY_RESUME`, and resume reintegration uses existing timing policy + heartbeat runner (no replacement).

### Evaluation harness (new)

The platform now includes an explicit **benchmark/evaluation harness** for autonomous paper/demo operation:

- objective session/run metrics across proposals, approvals, blocks, executions, reviews, PnL/equity, and safety events
- auditable run records via `EvaluationRun` + `EvaluationMetricSet`
- technical frontend route at `/evaluation` for snapshots, recent run comparisons, and guidance
- strict local-first boundary: no ML, no LLM, no real-money execution

### Experiment runner / strategy profiles (new)

The platform now includes an **experiment runner** for profile-based comparison across replay and live paper evaluation:

- persisted `StrategyProfile` configs (conservative/balanced/aggressive/custom)
- persisted `ExperimentRun` records for replay, live evaluation, and live-vs-replay comparison snapshots
- normalized metrics and `/api/experiments/comparison/` deltas to identify useful/conservative/stable behavior
- frontend route `/experiments` with profile cards, run launcher, run history, and side-by-side comparison table
- strict scope remains paper/demo only: no real money, no real execution, no ML/LLM tuning

### Governed tuning validation / champion-challenger paper loop (new)

The experiments layer now includes a controlled validation loop between `tuning_board` proposals and manual promotion review:

- consumes `TuningProposal` / `TuningProposalBundle` outputs without re-deriving proposals
- creates auditable `TuningExperimentRun` + `ExperimentCandidate` records
- runs explicit baseline/champion vs challenger comparisons in paper/replay-evaluation context
- stores `TuningChampionChallengerComparison` deltas with status (`IMPROVED`, `DEGRADED`, `MIXED`, `INCONCLUSIVE`, `NEEDS_MORE_DATA`)
- emits `ExperimentPromotionRecommendation` outcomes:
  - `PROMOTE_TO_MANUAL_REVIEW`
  - `KEEP_BASELINE`
  - `REQUIRE_MORE_DATA`
  - `REJECT_CHALLENGER`
  - `BUNDLE_WITH_OTHER_CHANGES`

API:
- `POST /api/experiments/run-tuning-validation/`
- `GET /api/experiments/tuning-candidates/`
- `GET /api/experiments/champion-challenger-comparisons/`
- `GET /api/experiments/promotion-recommendations/`
- `GET /api/experiments/tuning-validation-summary/`

Hard boundaries remain unchanged:
- no auto-apply of tuning proposals
- no auto-promotion to champion
- no real-money or broker/exchange execution

### Promotion governance board / manual adoption committee (new)

The `promotion_committee` layer now includes a formal **manual adoption governance flow** on top of `experiment_lab` outputs:

- consumes `ExperimentCandidate`, `TuningChampionChallengerComparison`, and `ExperimentPromotionRecommendation`
- builds auditable `PromotionReviewCycleRun` + `PromotionCase` + `PromotionEvidencePack` + `PromotionDecisionRecommendation`
- classifies readiness (`READY_FOR_REVIEW`, `NEEDS_MORE_DATA`, `DEFERRED`, `REJECTED`, `APPROVED_FOR_MANUAL_ADOPTION`)
- emits committee-facing recommendation types (`APPROVE_FOR_MANUAL_ADOPTION`, `DEFER_FOR_MORE_EVIDENCE`, `REJECT_CHANGE`, `REQUIRE_COMMITTEE_REVIEW`, `SPLIT_SCOPE_AND_RETEST`, `GROUP_WITH_RELATED_CHANGES`, `REORDER_PROMOTION_PRIORITY`)
- keeps a strict boundary: **validation ≠ automatic adoption**

API:
- `POST /api/promotion/run-review/`
- `GET /api/promotion/cases/`
- `GET /api/promotion/evidence-packs/`
- `GET /api/promotion/recommendations/`
- `GET /api/promotion/summary/`

Deliberate non-goals remain in force:
- no auto-promote / auto-apply
- no real-money execution
- no black-box planner authority

### Execution-aware replay / evaluation realism / readiness impact (new)

The platform now supports a practical execution realism bridge across replay, evaluation, experiments, and readiness:

- replay runs accept `execution_mode=naive|execution_aware` and `execution_profile=optimistic_paper|balanced_paper|conservative_paper`
- execution-aware replay routes orders through `execution_simulator` (paper orders, attempts, fills, partial/no-fill, slippage, cancel/expire)
- replay stores `execution_impact_summary` for auditable metrics:
  - `fill_rate`, `partial_fill_rate`, `no_fill_rate`
  - `avg_slippage_bps`, `execution_adjusted_pnl`, `execution_drag`
  - `execution_realism_score`, `execution_quality_bucket`
- evaluation snapshots include execution-adjusted metadata so historical snapshots are less optimistic than perfect-fill assumptions
- experiments can compare naive vs execution-aware metrics and expose execution drag deltas
- readiness now applies an explicit execution-realism penalty when evidence is weak or fill realism is poor

Still out of scope: real money, real routing, institutional microstructure modeling, complex hedging, and opaque planner authority.

### Prediction model governance (new)

Prediction training now includes a formal governance layer for predictor comparison:

- heuristic-vs-heuristic and heuristic-vs-XGBoost comparisons on offline datasets
- scope-aware evaluation (`demo_only`, `real_only`, `mixed`)
- evaluation profiles (`conservative_model_eval`, `balanced_model_eval`, `strict_calibration_eval`)
- auditable recommendation output:
  - `KEEP_HEURISTIC`
  - `KEEP_ACTIVE_MODEL`
  - `ACTIVATE_CANDIDATE`
  - `CAUTION_REVIEW_MANUALLY`
- explicit non-goal: no automatic model switching at runtime

### Prediction runtime hardening / calibrated probability review (new)

`prediction_agent` now includes a stronger runtime review layer for paper/demo operations:

- consumes filtered research triage candidates (shortlist/watchlist), not raw market universe
- builds auditable `PredictionRuntimeRun` + `PredictionRuntimeCandidate` + `PredictionRuntimeAssessment` + `PredictionRuntimeRecommendation`
- combines active model (if available), explicit heuristic fallback, runtime calibration, bounded narrative influence, and precedent caution
- emits recommendation-first outcomes for downstream handoff:
  - `SEND_TO_RISK_ASSESSMENT`
  - `SEND_TO_SIGNAL_FUSION`
  - `KEEP_FOR_MONITORING`
  - `IGNORE_NO_EDGE`
  - `IGNORE_LOW_CONFIDENCE`
  - `REQUIRE_MANUAL_PREDICTION_REVIEW`
- keeps scope unchanged: local-first, single-user, manual-first, paper/demo only, no real-money execution


The platform now also includes a controlled **autonomous continuous demo loop** (`/continuous-demo` + `/api/continuous-demo/*`):

- starts, pauses, resumes, and stops continuous background cycles
- supports single manual cycle execution for safe operator testing
- persists session + cycle audit trails
- reuses existing automation and semi-auto services
- remains strictly paper/demo only with explicit kill switch support

Still out of scope: real execution, exchange auth, distributed schedulers, websockets, and LLM agents.


### Incident commander / degraded mode orchestration (new)

A formal `incident_commander` backend layer now coordinates conservative failure handling across runtime, mission control, rollout, alerts/notifications, and operator queue:

- formal incident entities (`IncidentRecord`, `IncidentAction`, `IncidentRecoveryRun`)
- explicit degraded mode state (`DegradedModeState`)
- conservative mitigation policies (pause/degrade/rollback/disable auto-exec/manual review)
- bounded self-healing retries with full audit trail
- dedicated operator route `/incidents` for current degraded state + incident history

Still out of scope: real-money execution, real execution routing, opaque black-box remediation, and distributed orchestration.


### Operator cockpit / command center (new)

A new desktop-first `/cockpit` route now provides a **single-pane operational control** for manual-first supervision:

- central posture: runtime status, degraded mode, certification, and profile regime
- mission operations panel with cycle context and incident impact
- risk/exposure panel with portfolio throttle + `REVIEW_REQUIRED` position pressure
- execution/venue panel with broker-bridge validation, parity gaps, and reconciliation mismatches
- change-governance panel with promotion, rollout, and champion/challenger status
- severity-based attention queue (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`) with trace drill-down buttons
- quick actions that trigger existing controls (mission control, incident detection, certification, governance, rollout pause/rollback)
- live-read-only **Paper Portfolio Snapshot** card near Live Paper Autopilot for fast fake-money validation:
  - cash/equity/realized+unrealized PnL/open positions
  - aggregated open exposure + recent paper trades + latest snapshot timestamp
  - compact fallback (`Paper portfolio snapshot unavailable`) if paper endpoints are temporarily unavailable
  - reuses existing paper endpoints only (`/api/paper/account/`, `/api/paper/summary/`, `/api/paper/snapshots/`) and does not enable live execution

Scope remains unchanged: local-first, single-user, paper/sandbox only, and no real-money execution.

### Autonomy advisory board / insight action emitter (new)

The platform now includes a formal `autonomy_advisory` layer (`/api/autonomy-advisory/*` + `/autonomy-advisory`) to convert reviewed `autonomy_insights` outputs into auditable manual-first artifacts:

- consumes `CampaignInsight` and recommendation targets from `autonomy_insights`
- emits formal artifacts (`MEMORY_PRECEDENT_NOTE`, `ROADMAP_GOVERNANCE_NOTE`, `SCENARIO_CAUTION_NOTE`, `PROGRAM_POLICY_NOTE`, `MANAGER_REVIEW_NOTE`)
- tracks advisory runs, recommendation queue, blocked/manual-review states, and duplicate-skip outcomes
- keeps explicit links/stubs toward memory/feedback/program contexts without auto-applying changes

Out of scope remains explicit: no real-money trading, no real broker/exchange execution, no opaque auto-apply, and no black-box planner.

### Policy rollout guard / post-change baselining loop (new)

The stack now includes a dedicated `policy_rollout` layer (`/api/policy-rollout/*` + `/policy-rollout`) that closes the post-change governance loop after `policy_tuning` apply:

- starts a formal observation run from an **already applied** policy tuning candidate
- captures explicit **baseline snapshot** and **post-change snapshot**
- compares before/after deltas for approvals, friction, auto-success, incidents, and manual intervention
- emits recommendation-first outcomes:
  - `KEEP_CHANGE`
  - `REQUIRE_MORE_DATA`
  - `ROLLBACK_CHANGE`
  - `REVIEW_MANUALLY`
  - `STABILIZE_AND_MONITOR`
- supports **manual rollback only** (no silent auto-rollback), with audit metadata and optional approval-center gate

Deliberate non-goals remain unchanged: no real money, no real execution, no opaque auto-apply/auto-rollback planner, single-user local-first scope.

## What this scaffold does not include yet

- Real trading provider integrations (execution/auth).
- Note: real **read-only** market-data ingestion is now available for Kalshi and Polymarket.
- Authentication or user management.
- Real trading or provider execution logic.
- ML, forecasting models, or agent orchestration.
- Production deployment configuration.

## Technology stack

- **Frontend:** React, Vite, TypeScript
- **Backend:** Django, Django REST Framework, Celery
- **Data & messaging:** PostgreSQL, Redis
- **Developer tooling:** Docker Compose, Makefile, shell scripts

## Repository structure

```text
market-trading-bot/
├── apps/
│   ├── backend/
│   └── frontend/
├── docs/
│   ├── api/
│   ├── architecture/
│   └── prompts-codex/
├── infra/
│   ├── docker/
│   └── scripts/
├── libs/
│   ├── common-utils/
│   ├── feature-store/
│   ├── provider-core/
│   ├── provider-kalshi/
│   └── provider-polymarket/
├── services/
│   ├── execution-engine/
│   ├── market-discovery/
│   ├── postmortem-engine/
│   ├── probability-engine/
│   ├── risk-engine/
│   └── source-intelligence/
├── .env.example
├── .editorconfig
├── .gitignore
├── docker-compose.yml
└── Makefile
```

## Local setup

### Recommended flow: `start.py`

The repository now includes a project-specific launcher at the repo root:

```bash
python start.py
```

That default command is equivalent to:

```bash
python start.py up
```

What the launcher does for this monorepo:

- validates the expected repo structure (`apps/backend`, `apps/frontend`, `docker-compose.yml`)
- checks local prerequisites such as Python, Node.js, npm, and Docker Compose
- resolves `node`/`node.exe` and `npm`/`npm.cmd` explicitly on Windows so PowerShell and VS Code terminals behave correctly
- creates `.env` files from `.env.example` when they are missing
- creates `apps/backend/.venv` when needed
- installs backend requirements only when `requirements.txt` changes
- installs frontend dependencies only when `package.json` or `package-lock.json` changes
- starts PostgreSQL and Redis with Docker Compose
- runs Django migrations
- auto-seeds demo markets only when the database has no `Market` rows yet
- validates backend and frontend preparation before launching long-lived dev processes so the system is not left half-started
- starts the Django dev server and the Vite dev server in detached background mode by default
- waits for `http://localhost:8000/api/health/` and `http://localhost:5173/` to respond before declaring success
- opens the browser automatically to `http://localhost:5173/system` unless you disable it
- keeps a launcher state file in `.tmp/start-state.json` so `python start.py down` can stop launcher-managed processes later
- keeps the default workflow in a single console on Windows instead of opening two extra terminal windows
- optionally starts the local simulation loop

### Main launcher commands

```bash
python start.py
python start.py up
python start.py setup
python start.py status
python start.py down
python start.py seed
python start.py simulate-tick
python start.py simulate-loop
python start.py backend
python start.py frontend
```

### Launcher visual para Windows (`launcher_gui.py`)

Si prefieres un acceso visual compacto para uso local en Windows, puedes usar:

```bash
python launcher_gui.py
```

> En Windows, aunque lo abras con `python launcher_gui.py`, el launcher se relanza automáticamente con `pythonw.exe` (cuando existe junto al intérprete actual) para evitar la consola negra y que la GUI no dependa de dejar abierta esa terminal.

Este launcher **no reimplementa lógica**: delega en `start.py` y ejecuta:

- `full` → **Iniciar sistema completo**
- `lite` → **Iniciar modo liviano**
- `backend` → **Iniciar solo backend**
- `frontend` → **Iniciar solo frontend**
- `status` → **Revisar servicios**
- `stop` → **Detener servicios**

Layout compacto (sin resize manual en condiciones normales):

- **Arranque del sistema:** inicio completo/lite + repetir último inicio.
- **Servicios individuales:** backend/frontend/estado/stop.
- **Logs y monitoreo:** dashboard + panel interno de logs + accesos directos de logs.
- **Preferencias y debug:** toggles de navegador/debug/Ollama, timeout/modelo/base URL y smoke test.

Los botones se renderizan en **2 o 3 columnas según ancho de ventana**, con alturas y paddings más densos para reducir overflow vertical.

Incluye un bloque de estado rápido para:

- Docker
- Ollama service (API local viva)
- Ollama backend (si quedó habilitado para el backend lanzado)
- Backend
- Frontend

con estados `OK`, `STARTING`, `OFF`, `ENABLED` o `DISABLED`.

Flujo operador vs debug en GUI:

- **Modo operador (default):** `launcher_gui.py` envía `--gui-silent`, por lo que backend/frontend arrancan en detached/no-window (sin abrir consolas separadas), y mantiene apertura normal de navegador según toggle.
  - En Windows, el arranque silencioso usa un único camino de spawn sin ventana (`shell=False`, `DETACHED_PROCESS + CREATE_NO_WINDOW + STARTF_USESHOWWINDOW`) tanto para `full`/`lite` como para `backend`/`frontend`.
  - El frontend prioriza ejecutar Vite directo (`node apps/frontend/node_modules/vite/bin/vite.js ...`) y, como fallback, `node .../npm-cli.js`, para evitar wrappers visibles de `cmd.exe`.
  - El backend launcher-managed se ejecuta con `runserver --noreload` (también cuando se lanza en modo debug/separate windows), para evitar que el autoreloader cree un hijo fuera del ownership del launcher/state.
  - Cierre final de ownership en Windows: si el PID inicial del backend es solo bootstrap/intermedio, el launcher rebindea y guarda el PID hijo real (`python manage.py runserver ...`) en `.tmp/start-state.json`; además, la verificación de proceso vivo usa `tasklist` para evitar falsos negativos de `os.kill(..., 0)` en procesos detached. Con esto `Logs backend` y `down/cleanup` apuntan al proceso backend real.
  - El launcher guarda en `.tmp/start-state.json` los procesos **reales launcher-managed** (backend/frontend/ollama/sim-loop) con `pid`, `mode` y `log_file`, y el panel interno de logs consume ese mismo estado para `Logs backend` / `Logs frontend`.
- **Modo debug (checkbox):** habilita `--separate-windows` (y `--verbose` para comandos que lo soportan), dejando consolas visibles para diagnóstico.
- Esto aplica a arranques `full`, `lite`, `backend` y `frontend` desde la GUI.

Al cerrar `launcher_gui.py`, si hay procesos launcher-managed activos en `.tmp/start-state.json`, la GUI ofrece una decisión explícita:

- **Sí:** cerrar launcher y ejecutar cleanup (`python start.py down`) para detener servicios launcher-managed.
- **No:** cerrar launcher y dejar servicios corriendo.
- **Cancelar:** no cerrar la GUI.

La GUI ahora tiene un **panel interno plegable de logs** (tabs `Backend` / `Frontend`) para no depender de ventanas de consola:

- muestra últimas líneas (tail compacta),
- refresca en segundo plano sin congelar la UI,
- lee directamente los `log_file` launcher-managed desde `.tmp/start-state.json` (sin invocar `python start.py logs` en cada refresh),
- evita spawn repetido de subprocesos en Windows durante el refresco del panel (sin flashes de consola asociados al polling),
- permite auto-scroll opcional,
- incluye botones de actualizar, limpiar y copiar.

El botón de **Logs Ollama** se mantiene como salida puntual vía `start.py logs --service ollama`. Además, `start.py logs` endurece la salida Unicode en Windows para reemplazar caracteres no representables y evitar `UnicodeEncodeError` por `cp1252/charmap`.

El panel ahora expone controles separados para LLM local:

- **“Usar Ollama (shadow)”** → mapea a `--ollama enabled|disabled`.
- **“Activar señal auxiliar LLM”** → mapea a `--ollama-aux-signal enabled|disabled` (`OLLAMA_AUX_SIGNAL_ENABLED`).
- **“Timeout Ollama (s)”** (30/60/90/120) → mapea a `--ollama-env-timeout` (backend) y `--ollama-timeout` (probe de servicio).
- **“Modelo Ollama”** y **“Base URL Ollama”** para reutilizar esos valores tanto en el arranque como en el smoke test.
- **“Probar Ollama (smoke test)”** ejecuta `apps/backend/.venv/Scripts/python.exe apps/backend/manage.py run_llm_shadow_smoke --settings=config.settings.lite --model <modelo> --timeout <timeout> --json` (más `--aux-signal`/`--no-aux-signal` según toggle actual).

El timeout por defecto para backend queda elevado a **90 segundos** (`OLLAMA_TIMEOUT_SECONDS=90`) para modelos locales más lentos.

Al correr el smoke test desde GUI, el launcher pasa explícitamente el entorno del proceso (`OLLAMA_ENABLED`, `LLM_ENABLED`, `OLLAMA_AUX_SIGNAL_ENABLED`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_TIMEOUT_SECONDS`) para no depender de variables de la terminal interactiva y muestra un resumen legible + JSON completo en una ventana de resultados.

Si `apps/backend/.venv/Scripts/python.exe` no existe, el launcher muestra un error claro en GUI indicando que primero hay que preparar el backend (por ejemplo con `python start.py setup`).

Instalación mínima (si falta la dependencia):

```bash
pip install customtkinter
```

#### Acceso directo de escritorio (Windows)

1. Crea un acceso directo nuevo en el escritorio.
2. En **Destino**, usa tu `python.exe` seguido de la ruta absoluta al script:
   - Ejemplo: `"C:\\Python312\\python.exe" "C:\\ruta\\market-trading-bot\\launcher_gui.py"`
   - Opción recomendada para cero consola visible: usar directamente `pythonw.exe` en lugar de `python.exe`.
   - Ejemplo recomendado: `"C:\\Python312\\pythonw.exe" "C:\\ruta\\market-trading-bot\\launcher_gui.py"`
3. En **Iniciar en**, usa la carpeta del repo:
   - Ejemplo: `C:\\ruta\\market-trading-bot`
4. Opcional: cambia el icono del acceso directo para identificarlo como launcher local.

### Runtime modes: full vs lite

The launcher now supports two explicit local modes:

- **FULL mode (default):** PostgreSQL + Redis via Docker Compose, Django `config.settings.local`.
- **LITE mode (`--lite`):** SQLite, Docker skipped, Redis optional/disabled, Django `config.settings.lite`.

Examples:

```bash
python start.py --lite
python start.py setup --lite
python start.py up --lite
python start.py up --ollama enabled
python start.py up --lite --ollama enabled
python start.py up --ollama disabled
```

`--lite` can be used from notebooks or machines without Docker. In lite mode the launcher forces `--skip-infra`, runs migrations against SQLite, and keeps the frontend flow unchanged.

Useful optional flags:

```bash
python start.py --no-browser
python start.py --verbose
python start.py --separate-windows
python start.py up --no-seed
python start.py up --skip-seed
python start.py up --skip-infra
python start.py up --with-sim-loop
python start.py setup --skip-frontend
python start.py setup --skip-backend
python start.py setup --skip-install
python start.py up --lite
```

For V1 paper diagnostics where backend visibility matters (Run scan / Trial run / Extended run / Test Console start-stop), use:

```bash
python start.py up --verbose
```

That mode keeps Django attached to the current terminal so request logs, prints, errors, and tracebacks are visible live.  
You can also enable it through environment variables:

```bash
START_VERBOSE=1 python start.py up
# or
MTB_START_VERBOSE=1 python start.py up
```

### What each command does

- `python start.py` / `python start.py up`: validates prerequisites first, prepares the local environment, starts Postgres + Redis, runs migrations, seeds demo data if needed, launches backend + frontend in detached mode, waits for both services to respond, opens the browser by default, and then returns control to the same console.
- `python start.py up --verbose`: same setup flow, but keeps the backend process attached to the terminal so backend request/debug logs stay visible during live paper testing.
- `python start.py setup`: prepares `.env`, `.venv`, backend/frontend dependencies, infra (or skips infra in lite mode), migrations, and auto-seed logic without starting the dev servers.
- `python start.py status`: prints the current Python interpreter, backend venv python, Node/npm resolution, Docker Compose mode, env/dependency presence, process/runtime readiness, startup mode, and URLs.
- `python start.py down`: stops launcher-managed backend/frontend processes and runs `docker compose down` (or `docker-compose down`).
- `python start.py seed`: runs `python manage.py seed_markets_demo`.
- `python start.py simulate-tick`: runs one simulation tick with `python manage.py simulate_markets_tick`.
- `python start.py simulate-loop`: runs the existing loop command `python manage.py simulate_markets_loop`.
- `python start.py backend`: prepares and starts only the Django backend.
- `python start.py frontend`: prepares and starts only the Vite frontend.

### Lite mode limitations (intentional)

- SQLite is for local portability, not production concurrency.
- Redis is optional/disabled in lite mode; anything requiring external broker behavior should be treated as degraded local-demo behavior.
- Continuous/semi-auto/evaluation flows remain paper/demo oriented and suitable for local iteration, not long-running production sessions.

## Running each part manually

## Recommended launcher UX

The daily local-first workflow is now:

```bash
python start.py
```

That single command now:

1. validates prerequisites
2. prepares `.env`, backend, frontend, and local infra
3. runs migrations
4. auto-seeds demo data when needed
5. starts backend and frontend in background/detached mode
6. waits until backend and frontend really answer HTTP requests
7. opens `http://localhost:5173/system` automatically
8. prints a final “system ready” summary in the original console

If you want the older debug-style behavior with separate Windows terminals:

```bash
python start.py --separate-windows
python start.py up --separate-windows
```

If you do not want the browser to open automatically:

```bash
python start.py --no-browser
python start.py up --no-browser
```

To stop everything that the launcher started:

```bash
python start.py down
```

You can still use the existing manual commands if you want finer control.

### PostgreSQL and Redis

```bash
docker compose up -d postgres redis
docker compose down
```

### Backend

```bash
cd apps/backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

Healthcheck endpoint:

```text
GET http://localhost:8000/api/health/
```

### Frontend

```bash
cd apps/frontend
cp .env.example .env
npm install
npm run dev
npm run build
```

Important frontend environment variable:

```env
VITE_API_BASE_URL=http://localhost:8000
```

## Current modules

### Apps
- `apps/frontend`: local-first dashboard shell with multi-page navigation and backend health visibility.
- `apps/backend`: API scaffold and project configuration.

### Services
- `source-intelligence`
- `market-discovery`
- `probability-engine`
- `risk-engine`
- `execution-engine`
- `postmortem-engine`

Each service currently contains only a README describing its intended future responsibility.

### Libraries
- `provider-core`
- `provider-kalshi`
- `provider-polymarket`
- `feature-store`
- `common-utils`

Provider libraries now include a first read-only implementation for market-data ingestion (Kalshi + Polymarket) plus shared provider-core abstractions.

## Documentation

- `apps/frontend/README.md`: frontend setup, routing, healthcheck behavior, and local configuration.
- `docs/architecture/frontend-architecture.md`: frontend layout and routing decisions for this phase.
- `docs/architecture/monorepo-architecture.md`: initial architecture description.
- `docs/prompts-codex/README.md`: guidelines for future Codex-assisted tasks.
- `docs/api/README.md`: placeholder for future API reference material.

## Demo flow guide

The current local demo is intended to be exercised in this order:

1. open `/` to verify environment health and cross-module indicators
2. review `/signals` or `/markets` to find a market worth inspecting
3. open `/markets/:marketId` to review the market, run the demo risk check, and execute a paper trade
4. open `/portfolio` to inspect the new position, trade history, equity impact, and snapshot changes
5. open `/postmortem` to review the trade outcome and jump back to the related market or portfolio context

If the local environment is empty, you may still need to run some backend demo commands first:

```bash
cd apps/backend && python manage.py seed_paper_account
cd apps/backend && python manage.py generate_demo_signals
cd apps/backend && python manage.py generate_trade_reviews
```

## Helpful commands

```bash
python start.py
python start.py status
python start.py down
python start.py backend
python start.py frontend
make install-frontend
make install-backend
make frontend-dev
make frontend-build
make backend-dev
make backend-migrate
make backend-check
make infra-up
make infra-down
```

## Pending work

- Add domain data and APIs beyond the health monitoring scaffold.
- Upgrade placeholder pages into feature modules progressively.
- Introduce shared contracts for future provider adapters.
- Add containerization for the frontend and backend apps.
- Expand architecture decisions, contribution guidance, and test coverage.

## Summary

This repository is now ready to serve as the base for staged implementation. The current version is a clean, local-first scaffold designed to grow without introducing premature business logic.

## Guided demo automation

The repo now includes a guided demo automation layer that sits on top of the existing local workflow. It exposes explicit backend actions and a frontend `/automation` control center so an operator can move the demo forward without running every step from the terminal.

Included actions:

- simulation tick
- demo signal generation
- paper portfolio revalue
- trade review generation
- lightweight demo state sync
- full demo cycle orchestration

Out of scope by design:

- auto-trading
- periodic scheduling
- real background workers
- websockets
- autonomous agents
- real provider integrations

## Current end-to-end demo flow

The monorepo now supports a local-first demo workflow that looks like this:

`market -> signal -> risk -> policy -> trade -> portfolio -> review -> automation`

A new policy engine / approval rules layer now governs proposed demo trades before execution. It returns one of three explicit outcomes:

- `AUTO_APPROVE`
- `APPROVAL_REQUIRED`
- `HARD_BLOCK`

This layer is intentionally deterministic and auditable. It does **not** use ML, real providers, autonomous agents, or live auto-trading.


## Real data ingestion (read-only)

From `apps/backend` run:

```bash
python manage.py ingest_kalshi_markets --limit 50 --active-only
python manage.py ingest_polymarket_markets --limit 50 --active-only
```

These commands only ingest public market data. They do **not** place orders and do **not** require trading authentication.


## Safety hardening / guardrails (paper-only)

This repo now includes an explicit **safety guard** layer to harden demo operation before any future autonomy increase:

- exposure caps per market and globally
- auto-trade caps per cycle/session
- drawdown and unrealized-loss thresholds
- cooldown soft-stop and hard-stop transitions
- explicit kill switch policy with manual re-enable
- auditable safety events for warnings/stops/escalations

Still intentionally not implemented: real trading execution, real exchange auth, local LLM, advanced adaptive optimization.

### Learning memory / adaptive heuristics demo (new)

El sistema ahora incluye una capa de **learning memory heurística y auditable** (sin ML/LLM):

- persiste memoria de outcomes recientes desde postmortem/evaluation/safety
- genera ajustes conservadores activos por scope (`global`, `provider`, `source_type`, `signal_type`)
- influye de forma limitada en proposal/risk sin reemplazar policy
- expone `/learning` en frontend y `/api/learning/*` en backend

Sigue fuera de alcance: ML real, entrenamiento automático, LLM local, ejecución real y dinero real.


## Controlled learning loop integration (current)

The platform now closes a controlled learning loop across existing modules:

- automation and continuous demo can trigger a conservative learning-memory rebuild
- every rebuild is persisted as an auditable `LearningRebuildRun`
- rebuilt adjustments continue to influence proposal confidence/quantity and risk caution in later cycles
- defaults remain conservative (manual-first, no per-cycle aggressive rebuild)

Still intentionally out of scope:
- ML training/inference
- local LLM agents
- real money or real execution
- opaque autonomous tuning

### Real-data refresh pipeline hardening (new)

The project now includes a dedicated, auditable read-only sync pipeline for real providers (Kalshi + Polymarket):

- persisted sync run tracking (`ProviderSyncRun`)
- manual sync via API + management command
- provider health signal exposure (`last success`, `last failed`, `consecutive failures`, stale warning)
- strengthened snapshot ingestion path for real read-only markets
- conservative integration hooks for automation and continuous-demo

Still explicitly out of scope:
- real trading execution
- real exchange auth
- websocket/streaming infrastructure
- distributed scheduler/worker orchestration


## Autonomous real-market paper operation scope
- New backend module `real_market_ops` adds conservative autonomous scope for `real_read_only` markets with `paper_demo_only` execution.
- Eligibility centralizes provider health/freshness, paper tradability, open status, pricing sufficiency, and optional liquidity/volume/category constraints.
- API endpoints: `/api/real-ops/evaluate/`, `/api/real-ops/run/`, `/api/real-ops/runs/`, `/api/real-ops/status/`.
- Frontend route `/real-ops` provides controls for evaluation/run, scope summary, provider-sync awareness, and recent run audit table.
- Explicitly out of scope: real exchange auth, real execution adapters, websockets/streaming, and real-money trading.

### Portfolio-aware allocation demo (new)

El sistema ahora incluye una capa explícita de **portfolio-aware capital allocation / execution prioritization** en modo paper/demo:
- ranking heurístico y auditable de propuestas competidoras
- asignación conservadora de cantidad final según cash/exposición/límites
- historial de corridas y decisiones (`AllocationRun`, `AllocationDecision`)
- integración con `semi_auto_demo` y `real_market_ops` antes de autoejecución paper

Se mantiene fuera de alcance: optimización cuantitativa avanzada, Kelly, ML/LLM, y dinero real.

## Operator Queue / Escalation Center (new)

A new centralized operator queue is now available at:
- Backend API: `/api/operator-queue/*`
- Frontend route: `/operator-queue`

What it does:
- unifies approval-required and escalated exceptions in a single inbox
- supports approve/reject/snooze decisions with audit logs
- keeps execution mode strictly paper/demo only

Current source integrations:
- semi-auto pending approvals
- real-ops pending approvals and safety-escalated approvals

Explicitly still out of scope:
- real trading execution
- exchange authentication
- real money
- local LLM
- multi-user approval workflow

### Historical replay / backtest-like simulation demo (new)

The platform now includes a dedicated replay layer (`/replay`, `/api/replay/*`) to run controlled historical simulations using already persisted market snapshots.

Key boundaries:
- uses stored snapshots only (no live streaming dependency during replay)
- reuses proposal/risk/policy/allocation/safety flow where possible
- isolated replay paper account per run to avoid contaminating operational paper account
- audit-friendly persisted artifacts: run-level summary + step-level timeline
- still local-first and paper/demo only (no real money, no real execution)

### Go-live readiness / promotion gates (new)

The platform now includes a dedicated **readiness assessment layer** for formal promotion decisions in paper/demo mode:

- backend app: `apps/readiness_lab`
- API: `/api/readiness/*`
- frontend route: `/readiness`
- persisted `ReadinessProfile` and `ReadinessAssessmentRun`
- explicit gate outcomes (pass/fail/warning), blockers, and recommendations

Important boundary: this does **not** enable real money, real execution, exchange auth, or automatic go-live.

### Runtime promotion controller / operational mode governance (new)

The platform now includes explicit runtime governance for paper/demo autonomy at `/runtime` and `/api/runtime/*`.

Operational modes:
- `OBSERVE_ONLY`
- `PAPER_ASSIST`
- `PAPER_SEMI_AUTO`
- `PAPER_AUTO`

What this adds:
- a persisted runtime mode state (`current_mode`, `status`, `set_by`, rationale, metadata)
- auditable runtime transition logs
- explicit capability matrix per mode
- mode changes constrained by **readiness** + **safety**
- automatic conservative degradation when safety/readiness constraints tighten

Scope remains unchanged:
- paper/demo only
- no real-money execution
- no exchange auth
- no automatic promotion to real trading
- no local LLM integration

## Operator alerts / incident center / digest pipeline (new)

The platform now includes a dedicated **operator alerts layer** for paper/demo operations:

- backend app: `apps/backend/apps/operator_alerts`
- frontend route: `/alerts`
- API base: `/api/alerts/`

What it adds:
- persistent alerts with severity/status/source and dedupe key
- simple aggregation from operator queue, safety, runtime, sync, readiness, and continuous demo modules
- acknowledge/resolve workflow for exception triage
- digest records that summarize recent windows without manually checking multiple screens

What remains intentionally out of scope:
- external notifications (email/SMS/push/chat)
- websockets/realtime infra
- real money / real order execution
- LLM-driven incident narratives

## Notification delivery / escalation routing (new)

Se agregó una capa explícita de **notification delivery / escalation routing** para operadores, manteniendo `operator_alerts` como fuente de verdad del incidente:

- Backend nuevo: `apps.notification_center`
- Entidades: `NotificationChannel`, `NotificationRule`, `NotificationDelivery`
- Canales iniciales: `ui_only` (siempre), `webhook` simple, `email` opcional
- Endpoints:
  - `GET/POST /api/notifications/channels/`
  - `GET/POST /api/notifications/rules/`
  - `GET /api/notifications/deliveries/`
  - `GET /api/notifications/deliveries/<id>/`
  - `POST /api/notifications/send-alert/<alert_id>/`
  - `POST /api/notifications/send-digest/<digest_id>/`
  - `GET /api/notifications/summary/`
- Dedupe/cooldown: ventana por regla + supresión por fingerprint y cooldown por alerta/canal.
- Frontend nuevo: ruta `/notifications` con canales, reglas, historial, resumen y acciones manuales.

Fuera de alcance por diseño: ejecución real, dinero real, LLM local, campañas masivas, orquestación enterprise de mensajería.

### Automatic notification dispatch + digest automation (new)

`notification_center` now supports local-first automation without real-money execution:

- automatic immediate dispatch for relevant/open alerts (rule-driven, dedupe+cooldown preserved)
- automatic digest cycles with conservative cadence (`cycle_window` digests)
- persistence escalation for stale critical/high alerts and repeated warnings
- auditable delivery trace via `NotificationDelivery.trigger_source` (`manual`, `automatic`, `digest_automation`, `escalation`)
- automation state controls via API and `/notifications` UI

Still out of scope: real trading, distributed schedulers, websocket push, and complex multi-tenant notification campaigns.

## Local LLM integration layer (Ollama, new)

The backend now includes a **local-first LLM integration layer** for controlled narrative enrichment (not autonomous decisioning):

- provider: `LLM_PROVIDER=ollama`
- local endpoint: `OLLAMA_BASE_URL=http://localhost:11434`
- configurable chat model: `OLLAMA_CHAT_MODEL`
- configurable embedding model: `OLLAMA_EMBED_MODEL` (default `nomic-embed-text`)
- toggle + timeout: `LLM_ENABLED`, `OLLAMA_TIMEOUT_SECONDS`

Initial use cases:
- proposal thesis enrichment
- post-mortem enriched summary + lessons learned
- learning-note enrichment
- local embeddings endpoint for prototyping

Explicit boundary remains unchanged:
- no real money
- no real execution
- no LLM replacement of risk/policy/safety
- no autonomous LLM trading

## Narrative ingestion + research scan MVP (new)

A first local-first narrative scan/research block is now available:

- Backend app: `apps/backend/apps/research_agent`
- Frontend route: `/research`
- API root: `/api/research/*`

What it does in this phase:
- ingest configurable RSS sources
- deduplicate narrative items
- run structured narrative analysis using local LLM (Ollama) with degraded heuristic fallback
- create heuristic market links against read-only real/demo markets
- generate a persisted shortlist of research candidates with narrative-vs-market relation labels (`alignment` / `divergence` / `uncertainty`)

Out of scope remains unchanged:
- no real-money execution
- no real exchange execution
- no complex X/Twitter/Reddit crawling
- no vector DB/RAG stack
- no LLM authority over risk/policy/safety

## Prediction agent MVP (new)

Se agregó un `prediction_agent` local-first orientado a paper/demo:

- calcula `system_probability`, `market_probability`, `edge`, `confidence` y `rationale`
- persiste `PredictionRun` + `PredictionFeatureSnapshot` + `PredictionScore` para auditoría
- expone API en `/api/prediction/*` y UI en `/prediction`
- integra narrativa (`research_agent`) y ajustes conservadores (`learning_memory`) como señales auxiliares
- alimenta `proposal_engine` como contexto adicional, sin reemplazar risk/policy/safety

Fuera de alcance (intencional en esta fase):
- dinero real / ejecución real
- modelo XGBoost entrenado final
- autoentrenamiento opaco
- reemplazo de guardrails por LLM o por el prediction layer

## Prediction trained-model foundation (new)

The prediction stack now includes an offline training foundation for calibrated tabular models:

- historical dataset build from market snapshots
- initial binary label definition (`future_probability_up_24h`)
- XGBoost training + sigmoid calibration
- model artifact registry + active model switching
- runtime integration with heuristic fallback

Still out of scope: real execution, real money, continuous auto-training loops, AutoML, and replacing risk/policy/safety governance.

## Agent orchestration layer (new)

The platform now includes an explicit **agent orchestration layer** under `/api/agents/*` and frontend `/agents`.

What is included:
- registered agents (scan, research, prediction, risk, postmortem, learning)
- auditable `AgentRun`, `AgentPipelineRun`, and `AgentHandoff` records
- controlled pipelines:
  - `research_to_prediction`
  - `postmortem_to_learning`
  - `real_market_agent_cycle`
- structured handoff payload summaries for traceability

What is intentionally not included yet:
- real-money trading
- real execution routing
- opaque autonomous multi-agent planners
- black-box LLM authority over system decisions

This layer reuses existing modules (research/prediction/risk/postmortem/learning) and does not replace their internal domain logic.


## Risk agent refinement (paper/demo only)
- New `apps/backend/apps/risk_agent/` module introduces structured `RiskAssessment`, `RiskSizingDecision`, `PositionWatchRun`, and `PositionWatchEvent`.
- Separation of concerns is explicit: prediction estimates; risk evaluates/sizes; policy authorizes; safety limits; runtime governs mode.
- API endpoints: `POST /api/risk-agent/assess/`, `POST /api/risk-agent/size/`, `POST /api/risk-agent/run-watch/`, `GET /api/risk-agent/assessments/`, `GET /api/risk-agent/watch-events/`, `GET /api/risk-agent/summary/`.
- Frontend route `/risk-agent` provides assessment, sizing, watch loop, and audit history panels.
- Out of scope remains unchanged: no real money, no real execution, no production-grade Kelly optimizer, no exchange stop-loss automation.

## Postmortem multi-agent board (new)

The platform now includes a local-first **postmortem board / loss review committee**:

- runs explicit perspective reviewers (narrative, prediction, risk, runtime, learning)
- stores auditable per-perspective records and a final structured conclusion
- integrates into learning memory with conservative handoff
- adds an explicit agent pipeline: `postmortem_board_cycle`
- remains strictly paper/demo only with no real-money or real-execution path

## Research universe scanner / triage board (new)

`research_agent` now includes a formal **universe scanner + market triage board** layer:

- explicit `MarketUniverseScanRun` runs with auditable counters (considered, filtered, shortlisted, watchlist)
- transparent `MarketTriageDecision` records with score, status, reasons, and flags
- explicit `PursuitCandidate` outputs for markets worth pursuing (`shortlisted` / `watch`)
- profile-based thresholds (`conservative_scan`, `balanced_scan`, `broad_scan`)
- narrative remains a contextual boost/caution signal (not a mandatory gate)
- handoff path from triage board to prediction pipeline (`run-triage-to-prediction`)

Scope remains local-first and **paper/demo only**: no real money, no real execution, no opaque optimizer/planner.


### Signal fusion agent / opportunity board (new)

A formal signal fusion layer now exists inside `apps.signals` to consolidate:
- research triage/pursuit output
- prediction scores (system probability, edge, confidence)
- risk assessment/sizing
- runtime + safety constraints

This layer produces ranked `OpportunitySignal` records and explicit `ProposalGateDecision` outputs before proposal generation.

Still out of scope:
- real-money trading
- real execution
- opaque planners/optimizers
- LLM final authority

## Opportunity supervisor cycle (new)

A new backend+frontend layer now provides an auditable **end-to-end autonomous opportunity cycle** in **paper/demo mode only**.

- Backend module: `apps/backend/apps/opportunity_supervisor/`
- API base: `/api/opportunities/*`
- Frontend route: `/opportunities`

Cycle flow:
1. signal-fusion run (research + prediction + risk context)
2. proposal generation for proposal-ready opportunities
3. allocation pre-check per generated proposal
4. governance path resolution using runtime + policy + safety
5. final path persistence (`WATCH`, `PROPOSAL_ONLY`, `QUEUE`, `AUTO_EXECUTE_PAPER`, `BLOCKED`)

Explicitly still out of scope:
- real-money execution
- exchange auth/order routing
- opaque free-form planner

### Mission control loop (new)

The platform now includes a formal **mission control** layer (`/mission-control`, `/api/mission-control/*`) to run periodic autonomous paper/demo operations with explicit loop governance:

- persistent mission sessions, cycles, and step-level traces
- explicit start/pause/resume/stop/run-cycle controls
- cadence-based optional steps (research/universe scan, risk watch, digest, postmortem refresh, learning rebuild)
- `opportunity_supervisor` remains the central execution-path engine inside each cycle
- runtime governor + safety guard remain authoritative (mission control degrades/skips when blocked)
- no real-money execution and no real trading path

Out of scope remains unchanged: distributed schedulers, cluster orchestration, and real execution.

## Portfolio governor / exposure manager (new)

Se añadió una capa formal de gobernanza de cartera (`apps/backend/apps/portfolio_governor`) para paper/demo only:

- snapshot agregado de exposición (equity, cash, exposure total, concentración por market/provider/category, drawdown proxy)
- señales de régimen auditables (`normal`, `concentrated`, `drawdown_caution`, `capital_tight`, etc.)
- decisión de throttling global (`NORMAL`, `CAUTION`, `THROTTLED`, `BLOCK_NEW_ENTRIES`)
- integración con `opportunity_supervisor`, `mission_control`, `runtime_governor` y `safety_guard`

Scope explícito:
- sí: throttling transparente por reglas
- no: dinero real, ejecución real, hedging complejo, optimizador institucional, planner opaco

## Adaptive profile manager / meta-governance (new)

A formal paper/demo-only `profile_manager` layer now coordinates adaptive operating profiles across research, signals, opportunity supervisor, mission control, and portfolio governor.

- classifies regime (`NORMAL`, `CAUTION`, `STRESSED`, `CONCENTRATED`, `DRAWDOWN_MODE`, `DEFENSIVE`, `BLOCKED`)
- emits auditable `ProfileDecision` records with reason codes and constraints
- separates recommendation vs application (`RECOMMEND_ONLY`, `APPLY_SAFE`, `APPLY_FORCED`)
- treats runtime/safety/readiness as higher authority and never bypasses them
- exposes `/profile-manager` UI + `/api/profile-manager/*` endpoints

Still out of scope: real-money execution, opaque planner behavior, RL/ML meta-controller, and LLM final authority.


## Paper execution realism layer
- Added `execution_simulator` to model paper order lifecycle (`PaperOrder`, `PaperExecutionAttempt`, `PaperFill`) with partial/no-fill, slippage, cancel/expire handling.
- This layer is **paper/demo only** and intentionally excludes real routing/exchange execution.

## Champion-Challenger shadow benchmark supervisor (new)

The platform now includes a dedicated **champion-challenger shadow mode** (`/champion-challenger` + `/api/champion-challenger/*`) for continuous live-paper benchmarking:

- explicit `StackProfileBinding` for champion and challenger stacks
- shadow-only benchmark runs (`ChampionChallengerRun`) with no real-money and no real execution
- execution-aware comparison metrics (fill rate, partial/no-fill, execution-adjusted pnl, execution drag)
- decision-divergence and risk/review pressure deltas
- recommendation output for governance follow-up:
  - `KEEP_CHAMPION`
  - `CHALLENGER_PROMISING`
  - `CHALLENGER_UNDERPERFORMS`
  - `REVIEW_MANUALLY`

Design boundaries:
- no automatic champion switching
- no hidden planner authority
- no RL auto-optimization
- no real-money execution

This complements prediction model governance and profile manager evidence without duplicating them.

## Semantic memory / precedent retrieval layer (new)

A local-first semantic memory layer is now available at `apps/backend/apps/memory_retrieval` with frontend visibility in `/memory`.

What it adds:
- formal memory entities: `MemoryDocument`, `MemoryRetrievalRun`, `RetrievedPrecedent`
- local embedding generation via existing `llm_local` embeddings (Ollama-compatible)
- simple in-process cosine retrieval (no external vector DB required)
- auditable run/result traceability for precedent retrieval
- case-based summary for caution signals, failure modes, and lessons learned

Primary API endpoints:
- `POST /api/memory/index/`
- `POST /api/memory/retrieve/`
- `GET /api/memory/documents/`
- `GET /api/memory/retrieval-runs/`
- `GET /api/memory/retrieval-runs/<id>/`
- `GET /api/memory/summary/`

Integrated assist endpoints:
- `POST /api/research/precedent-assist/`
- `POST /api/prediction/precedent-assist/`
- `POST /api/risk-agent/precedent-assist/`
- `POST /api/postmortem-board/precedent-compare/`

Out of scope remains unchanged: real money, real execution, heavy enterprise RAG stack, opaque planners.

### Stack promotion committee / controlled evolution pipeline (new)

A formal `promotion_committee` layer now provides conservative and auditable stack-change governance in paper/demo mode:

- consolidates evidence from champion-challenger, readiness, execution-aware deltas, profile governance, portfolio governor context, model governance, and precedent warnings
- emits clear recommendation codes:
  - `KEEP_CURRENT_CHAMPION`
  - `PROMOTE_CHALLENGER`
  - `EXTEND_SHADOW_TEST`
  - `REVERT_TO_CONSERVATIVE_STACK`
  - `MANUAL_REVIEW_REQUIRED`
- distinguishes recommendation-only vs explicit manual apply
- stores review runs + decision logs for traceability
- exposes `/promotion` UI route and `/api/promotion/*` API endpoints

Still out of scope:
- real money
- real execution
- opaque auto-promotion or auto-switching
- RL/auto-optimization


### Stack rollout manager / canary promotion / rollback guardrails (new)

A new `rollout_manager` layer now operationalizes promotion recommendations with explicit gradual rollout in paper/demo mode:

- explicit rollout plans (`SHADOW_ONLY`, `CANARY`, `STAGED`) with deterministic canary percentage routing
- persisted rollout runs with routed/champion/challenger/canary counters
- explicit guardrail events and rollout decisions (`CONTINUE_ROLLOUT`, `PAUSE_ROLLOUT`, `ROLLBACK_NOW`, `COMPLETE_PROMOTION`, `EXTEND_CANARY`)
- explicit rollback action back to champion-only routing with auditable reason
- integration touchpoints with mission control and opportunity supervisor

Boundary remains strict:
- no real-money execution
- no real order routing
- no opaque full auto-switching

### Chaos lab / fault injection / resilience benchmark (new)

The platform now includes a formal `chaos_lab` layer to actively validate resilience in paper/demo mode:

- controlled and reversible fault injection scenarios (`/api/chaos/experiments/`, `/api/chaos/run/`)
- auditable run traces (`ChaosRun`, `ChaosObservation`)
- resilience benchmark snapshots (`ResilienceBenchmark`) with detection/mitigation/recovery metrics and a simple transparent score
- explicit integration with `incident_commander`, `mission_control`, `rollout_manager`, alerts, notifications, and operator queue

Scope boundaries remain unchanged: no real money, no real execution, no distributed chaos orchestration.


### Operational certification board / paper go-live gate (new)

The platform now includes a formal `certification_board` layer for **paper-only** operational certification.

What it adds:
- consolidated evidence snapshot across readiness, chaos/resilience, incidents, champion/challenger, promotion, rollout, runtime/safety, profile and portfolio governance, and execution-aware evaluation
- explicit certification levels and recommendation codes
- auditable operating envelope output (autonomy limits, entry/sizing caps, profile constraints)
- manual-first run/apply workflow with clear logs

What it explicitly does not add:
- real money
- real order execution
- automatic opaque go-live
- auto-promotion to real capital


### Broker bridge sandbox / dry-run routing readiness layer (new)

A new `broker_bridge` layer now prepares the platform for eventual real execution **without crossing into real trading**:

- maps internal sources (currently paper orders and explicit manual payloads) into `BrokerOrderIntent`
- validates intents against certification envelope, runtime, safety, degraded mode, and open critical incidents
- records a `BrokerDryRun` simulated broker response (`accepted`, `rejected`, `hold`, `needs_manual_review`)
- creates operator queue review context when blocked/manual review is required
- exposes `/api/broker-bridge/*` endpoints and frontend route `/broker-bridge`

Boundary remains strict:
- no real broker credentials
- no real order routing
- no real money or account reconciliation

### Go-live rehearsal gate + capital firewall (new)

The platform now includes a formal `go_live_gate` layer to rehearse final pre-live workflows while still blocking live execution by default:

- persisted pre-live checklist runs
- manual approval requests
- final rehearsal run on broker-like intents (dry-run only)
- explicit capital firewall rules that keep live transition disabled
- API endpoints at `/api/go-live/*` and frontend route `/go-live`

This is a preparation layer only. Still out of scope: live credentials, live broker routing, real money, and real order submission.

## Execution venue abstraction (new)

A new backend/frontend layer now formalizes the final **execution venue contract** without enabling any real routing:

- Backend app: `apps/backend/apps/execution_venue`
- Frontend route: `/execution-venue`
- API base: `/api/execution-venue/*`

What it adds:
- canonical external order payload model (`VenueOrderPayload`)
- normalized venue response model (`VenueOrderResponse`)
- capability contract (`VenueCapabilityProfile`) with `live_supported=false`
- parity harness (`VenueParityRun`) to compare broker bridge dry-run, simulator context, and sandbox adapter behavior
- default `NullSandboxVenueAdapter` that never submits real orders

Still explicitly out of scope:
- broker credentials
- real broker/exchange connectivity
- live order placement
- real-money execution or reconciliation

## Venue account mirror / reconciliation sandbox (new)

A new `venue_account` layer completes the **incoming external bridge** in sandbox mode:

- canonical external-style snapshots for account, balances, orders, and positions
- mirror-building from existing `execution_venue` payload/response artifacts plus `execution_simulator`/`paper_trading` state
- formal reconciliation runs (`PARITY_OK` / `PARITY_GAP`) and explicit issue types (missing order mappings, fill drift, status mismatch, balance drift, stale snapshot)
- frontend route `/venue-account` for operational parity visibility

Boundary remains strict:
- sandbox-only (`SANDBOX_ONLY`)
- no broker credentials
- no real account connections
- no real order placement or real-money execution

## Connector Lab: venue connector certification suite (new)

A new sandbox-only **connector_lab** boundary is now available to certify future venue adapters before any read-only/live integration.

- Backend API under `/api/connectors/*` runs formal qualification suites for capabilities, payload mapping, response normalization, account mirror, and reconciliation.
- Readiness outputs include recommendation codes such as `SANDBOX_CERTIFIED`, `READ_ONLY_PREPARED`, `INCOMPLETE_MAPPING`, `RECONCILIATION_GAPS`, and `NOT_READY`.
- Frontend route `/connectors` provides qualification controls, readiness card, case results table, and recent runs.
- This does **not** add real broker connectivity, credentials, live routing, real orders, or real money.

## Unified trace explorer / decision provenance (new)

The platform now includes a dedicated local-first provenance layer for end-to-end auditing without rewriting existing modules:

- Backend app: `apps/backend/apps/trace_explorer`
- API base: `/api/trace/*`
- Frontend route: `/trace`

What it adds:
- trace roots (`market`, `opportunity`, `proposal`, `paper_order`, `venue_order_snapshot`, `incident`, `mission_cycle`)
- trace nodes and causal edges across research → prediction → risk → signals → proposal → allocation → execution → venue → incidents
- unified inclusion of agent orchestrator runs/handoffs and memory precedent use
- compact provenance snapshot for operator/debug/audit workflows
- auditable query history (`TraceQueryRun`)

Still out of scope:
- real money
- live broker execution
- distributed enterprise graph infrastructure
- opaque planner authority
- multi-user enterprise tenancy


## Runbook engine / operator playbooks

The platform now includes a manual-first **runbook engine** for guided remediation workflows.

- Backend module: `apps/backend/apps/runbook_engine/`
- API surface: `/api/runbooks/*`
- Frontend route: `/runbooks`

This layer orchestrates and records operator workflows for incidents, degraded mode, rollout/certification/venue parity issues, queue pressure, and related operational states. It reuses existing module actions (mission control, incidents, rollout, certification, venue reconciliation, trace) and does **not** introduce real money, live execution, or opaque automation.

### Trust-tiered automation policy matrix (new)

The stack now includes a formal **automation policy matrix / supervised runbook autopilot** layer:

- explicit automation profiles (`conservative_manual_first`, `balanced_assist`, `supervised_autopilot`)
- explicit trust tiers (`MANUAL_ONLY`, `APPROVAL_REQUIRED`, `SAFE_AUTOMATION`, `AUTO_BLOCKED`)
- auditable decisions for every evaluated action
- explicit action logs for every auto-execution attempt
- effective tier downgrade by runtime/safety/certification/degraded posture
- hard block for live-execution domains

New operator route: `/automation-policy`.

Scope remains unchanged: local-first, single-user, and paper/sandbox only.

### Supervised runbook autopilot (new)

A new **supervised runbook autopilot / approval-aware closed-loop remediation executor** now extends `runbook_engine` without replacing manual workflows:

- per-step policy resolution through `automation_policy` trust tiers
- safe actions can auto-execute step-by-step
- orchestration pauses for `APPROVAL_REQUIRED` or `MANUAL_ONLY`
- orchestration blocks on guardrail/policy `BLOCKED`
- explicit approval checkpoints, resume, and step retry with audit trails
- cockpit now surfaces paused/blocked autopilot pressure

Strict boundaries remain unchanged:
- local-first
- single-user
- paper/sandbox only
- no real money
- no real execution
- no black-box autonomous remediation

### Approval center / unified decision gates (new)

A new manual-first `/approvals` control plane now centralizes human decisions that were previously scattered across modules.

- Backend app: `apps/backend/apps/approval_center`
- Central entities: `ApprovalRequest`, `ApprovalDecision`
- Sources integrated now: runbook checkpoints, go-live approval requests, and `operator_queue` items marked `approval_required`
- Explicit actions: approve / reject / expire / escalate
- Every decision is auditable and links back to source context + trace roots
- Approving go-live requests in this phase **does not enable live trading** (still rehearsal + paper/sandbox only)

Out of scope remains unchanged: no real money, no real execution, no opaque black-box automation, no enterprise multi-user approval chains.


### Trust calibration governance loop (new)

A dedicated `trust_calibration` layer now closes the human-feedback loop between `approval_center` and `automation_policy` with explicit, auditable analytics.

- consolidates approval outcomes, automation decisions/action logs, and incident aftermath into feedback snapshots
- computes explicit friction/success/reversal metrics by action domain
- emits conservative recommendation-only trust-tier suggestions (`PROMOTE_TO_SAFE_AUTOMATION`, `KEEP_APPROVAL_REQUIRED`, `DOWNGRADE_TO_MANUAL_ONLY`, `BLOCK_AUTOMATION_FOR_ACTION`, `REQUIRE_MORE_DATA`, `REVIEW_RULE_CONDITIONS`)
- adds frontend route `/trust-calibration` with summary cards, metrics table, recommendation panel, and run history
- no auto-apply, no real-money execution, no real routing

### Policy tuning board / recommendation-to-approval workflow (new)

The platform now includes a formal `policy_tuning` layer that turns trust calibration recommendations into explicit, auditable policy change candidates.

- recommendation source remains `trust_calibration`
- operational policy authority remains `automation_policy`
- new explicit flow: candidate -> review decision -> manual apply -> application log
- before/after snapshots persisted for traceability
- frontend board available at `/policy-tuning`

Still out of scope:
- auto-apply without approval
- real money
- real execution
- opaque planners / black-box learning
- complex multi-user governance


### Autonomy stage manager / domain-level envelopes (new)

The stack now includes `autonomy_manager` as a conservative domain-level governance layer above action-level policy tuning:

- groups related action types into auditable operational domains
- tracks explicit domain stages (`MANUAL`, `ASSISTED`, `SUPERVISED_AUTOPILOT`, `FROZEN`, `ROLLBACK_RECOMMENDED`)
- consolidates evidence from trust calibration, policy rollout, incidents, approval friction, and certification posture
- emits recommendation-first domain transitions
- keeps stage changes manual-first with explicit apply/rollback and approval-center integration for higher-impact changes

Scope stays unchanged: local-first, single-user, paper/sandbox only, no real-money execution, and no opaque auto-promotion planner.

### Autonomy rollout board / domain transition baselining (new)

A dedicated `autonomy_rollout` layer now closes the post-change loop for domain stage transitions:

- starts monitoring from an **already APPLIED** autonomy transition
- captures explicit baseline and post-change snapshots per domain
- compares before/after deltas for approvals, friction, blocked actions, incidents, and degraded context
- emits recommendation-first outcomes:
  - `KEEP_STAGE`
  - `REQUIRE_MORE_DATA`
  - `FREEZE_DOMAIN`
  - `ROLLBACK_STAGE`
  - `REVIEW_MANUALLY`
  - `STABILIZE_AND_MONITOR`
- supports auditable **manual rollback only**, optionally approval-gated
- includes conservative cross-domain warning notes when related incident/degraded signals are detected

Scope remains local-first and paper/sandbox only: no real money, no real execution, no silent auto-rollback.

### Autonomy roadmap board (new)

A new `autonomy_roadmap` layer now governs **cross-domain autonomy progression** as a staged portfolio (not just per-domain transitions):

- explicit dependency mapping between autonomy domains (`requires_stable`, `blocks_if_degraded`, `recommended_before`, `incompatible_parallel`)
- recommendation-first roadmap plans with blocked/frozen domains, sequence suggestions, and optional bundles
- strict manual-first boundary: no automatic multi-domain promotion or hidden planner behavior
- cockpit and autonomy pages now link to `/autonomy-roadmap` for global roadmap visibility

Key API surface:
- `GET /api/autonomy-roadmap/dependencies/`
- `POST /api/autonomy-roadmap/run-plan/`
- `GET /api/autonomy-roadmap/plans/`
- `GET /api/autonomy-roadmap/plans/<id>/`
- `GET /api/autonomy-roadmap/recommendations/`
- `GET /api/autonomy-roadmap/summary/`

Still out of scope:
- real-money flows
- real execution
- opaque automatic multi-domain promotion


### Autonomy scenario lab (new)

A new `autonomy_scenario` layer adds a **roadmap simulation / bundle what-if evaluator** on top of existing autonomy governance:

- compares scenario options (single domain, sequence, bundle, freeze+promote, delay-until-stable)
- estimates dependency conflict risk, approval friction, degraded/incident exposure, rollback hints, and approval-heavy posture
- persists auditable simulation runs (`AutonomyScenarioRun`) with per-option risk and recommendation records
- emits recommendation-first outcomes such as `BEST_NEXT_MOVE`, `SAFE_BUNDLE`, `SEQUENCE_FIRST`, `DELAY_UNTIL_STABLE`, `DO_NOT_EXECUTE`, and `REQUIRE_APPROVAL_HEAVY`

Hard boundaries remain unchanged: manual-first, simulation-only, paper/sandbox only, no real-money or real-execution paths, and no auto-apply.


### Autonomy campaign board / staged transition program (new)

The platform now includes `autonomy_campaign` as the formal handoff layer between roadmap/scenario recommendations and staged manual-first execution programs.

- source binding: roadmap plan, scenario run, or manual bundle
- wave/step/checkpoint model for transparent staged execution
- explicit controls: create/start/resume/abort
- approval-center checkpoint integration and resume-after-approval
- rollout monitor + observation checkpoint orchestration (without duplicating autonomy_rollout)
- cockpit and frontend route integration at `/autonomy-campaigns`

Explicit non-goals remain: no real money, no real execution, no opaque auto-promotion planner.

### Autonomy program control tower / campaign concurrency guard (new)

The stack now includes an explicit **program-level governance layer** for autonomy campaigns:

- backend app: `apps/backend/apps/autonomy_program`
- frontend route: `/autonomy-program`
- purpose: coordinate multiple autonomy campaigns safely as one program (not isolated runs)

What it adds:
- global program posture (`NORMAL`, `CONSTRAINED`, `HIGH_RISK`, `FROZEN`)
- explicit concurrency rules (`max_active_campaigns`, `incompatible_domains`, degraded/incident/observation blocks)
- campaign health snapshots (checkpoints, approvals, rollout warnings, incident/degraded impact)
- recommendations (`PAUSE_CAMPAIGN`, `REORDER_QUEUE`, `HOLD_NEW_CAMPAIGNS`, etc.)
- optional pause gating with approval-center handoff

What it does **not** add:
- real-money trading
- real execution
- opaque multi-campaign mass auto-orchestration
- black-box planner behavior

### Autonomy scheduler / campaign admission board (new)

A dedicated `autonomy_scheduler` layer now governs **pending campaign admission** into the autonomy program:

- explicit campaign admission queue and statuses (`PENDING`, `READY`, `DEFERRED`, `BLOCKED`, `ADMITTED`, `EXPIRED`)
- formal safe-start windows (`OPEN`, `UPCOMING`, `CLOSED`, `FROZEN`) with capacity and posture/domain constraints
- auditable scheduler planning runs + recommendation records
- recommendation-first actions (`SAFE_TO_ADMIT_NEXT`, `WAIT_FOR_WINDOW`, `BLOCK_ADMISSION`, `REORDER_ADMISSION_QUEUE`, `REQUIRE_APPROVAL_TO_ADMIT`)
- manual-first controls for admit/defer (no mass auto-start)

This module is intentionally adjacent to existing autonomy layers:
- `autonomy_campaign`: still owns campaign execution internals
- `autonomy_program`: still owns active campaign coexistence posture/rules
- `autonomy_scheduler`: now owns candidate admission ordering and safe-start timing

Still out of scope: real-money execution, real broker routing, distributed schedulers, opaque planners, multi-user orchestration.


### Autonomy launch control / preflight start gate (new)

A new `autonomy_launch` layer now sits between `autonomy_scheduler` admission and `autonomy_campaign` start:

- evaluates admitted/ready campaigns for **start-now readiness** under explicit preflight checks
- persists auditable `LaunchReadinessSnapshot`, `LaunchAuthorization`, `LaunchRun`, and `LaunchRecommendation` records
- blocks unsafe starts when posture/window/incidents/degraded/rollout pressure/checkpoints/approvals are not safe
- keeps a manual-first loop with explicit `authorize` / `hold` actions
- powers a new operator board at `/autonomy-launch` for readiness, blockers, recommendations, and authorization state

Scope remains unchanged: local-first, single-user, paper/sandbox only, and no opaque mass auto-start orchestration.

### Autonomy activation gateway / authorized start handoff (new)

A new `autonomy_activation` layer now sits after `autonomy_launch` authorization and before `autonomy_campaign.start`.

What it adds:
- consumes `LaunchAuthorization(AUTHORIZED)` records
- revalidates posture/window/conflicts/incidents at actual dispatch time
- executes explicit, auditable manual dispatch into campaign start
- records activation outcomes (`STARTED`, `BLOCKED`, `FAILED`, `EXPIRED`)
- emits dispatch recommendations and run summaries for cockpit/trace visibility

What it does **not** add:
- real-money/live broker execution
- opaque mass auto-start
- distributed scheduler orchestration
- multi-user enterprise workflow

### Autonomy operations monitor / active campaign runtime board (new)

The platform now includes a formal `autonomy_operations` layer for **active campaign runtime supervision**.

What it adds:
- runtime snapshots for started campaigns (wave/step/checkpoint/progress/stall pressure)
- explicit operational attention signals (`OPEN`/`ACKNOWLEDGED`)
- auditable monitor runs and recommendation outputs (`CONTINUE`, `PAUSE`, `ESCALATE`, `REVIEW_FOR_ABORT`, etc.)
- new operator route `/autonomy-operations` integrated with activation/campaign/approvals/trace/cockpit

What it does not change:
- `autonomy_campaign` remains execution authority
- `autonomy_activation` remains dispatch/start authority
- `autonomy_program` remains global posture authority

Scope remains local-first, single-user, paper/sandbox only, with manual-first controls and no opaque auto-remediation.


### Autonomy intervention control / manual remediation gateway (new)

A new `autonomy_intervention` layer now formalizes **manual-first interventions** on active autonomy campaigns:

- auditable `CampaignInterventionRequest`, `CampaignInterventionAction`, `InterventionRun`, and `InterventionOutcome`
- explicit actions: pause, resume, escalate-to-approval, review-for-abort, clear-to-continue
- policy validation against campaign terminal state, runtime blockers, incident pressure, and program frozen posture
- approval-center integration for sensitive interventions
- dedicated backend API under `/api/autonomy-interventions/*` and frontend board at `/autonomy-interventions`

Still out of scope: real money, real broker/exchange execution, opaque auto-remediation, and multi-user orchestration.

### Autonomy recovery board / paused campaign resolution (new)

The stack now includes a formal `autonomy_recovery` governance layer for campaigns that are paused, blocked, escalated, or pending disposition after intervention:

- candidate discovery for paused/blocked/recently intervened campaigns
- explicit blocker consolidation (approvals/checkpoints/incidents/program posture/domain locks)
- auditable recovery snapshots + runs + recommendations
- conservative recommendations: keep paused, resume-ready, require more recovery, review-for-abort, close-candidate, and recovery-priority reorder
- manual-first approval hooks for sensitive resume/close decisions
- frontend route `/autonomy-recovery` for operator review and traceable next actions

Scope remains unchanged: local-first, single-user, paper/sandbox only, with no real broker/exchange execution and no opaque auto-recovery.


### Autonomy disposition board / campaign closure committee (new)

The platform now includes a formal `autonomy_disposition` governance layer for final campaign lifecycle disposition:

- consolidates campaigns that are ready to close, abort, retire, or remain open
- records auditable `CampaignDisposition` outcomes with rationale, blockers, and before/after state
- generates disposition runs + recommendations and supports approval-center gating for sensitive actions
- exposes a dedicated UI route at `/autonomy-disposition` for manual-first review and apply

This layer consumes recovery/intervention/operations context and does **not** replace campaign execution, recovery evaluation, or program posture authority. Scope remains local-first, single-user, and paper/sandbox only.


### Autonomy closeout board / campaign archive dossier (new)

The platform now includes `autonomy_closeout`, a post-disposition governance layer that converts final campaign outcomes into auditable closeout dossiers and reusable learning handoffs:

- consolidates post-disposition closeout candidates with explicit ready/blocked posture
- persists `CampaignCloseoutReport`, `CloseoutFinding`, `CloseoutRun`, and `CloseoutRecommendation`
- derives structured lifecycle/blocker/incident/intervention/recovery summaries
- emits explicit handoff stubs for `memory_retrieval`, `postmortem-board`, and roadmap/scenario feedback
- keeps completion manual-first (`POST /api/autonomy-closeout/complete/<campaign_id>/`) with blocker/approval checks

Boundaries:
- does **not** replace `autonomy_disposition` as final disposition authority
- does **not** auto-archive, auto-learn opaquely, or auto-apply roadmap changes
- remains local-first, single-user, and paper/sandbox only

### Autonomy followup board (new)

The platform now adds a formal `autonomy_followup` layer that sits after `autonomy_closeout`:

- consumes closeout reports/findings/recommendation context (without replacing closeout)
- emits auditable manual-first handoffs to memory, postmortem request routing, and roadmap/scenario feedback stubs
- records followup history (`EMITTED`, `BLOCKED`, `DUPLICATE_SKIPPED`, etc.) and deduplicates repeated emissions
- provides `/autonomy-followup` UI + `/api/autonomy-followup/*` endpoints for candidates, run-review, summary, recommendations, and campaign emission

Still out of scope: real-money execution, broker/exchange live routing, opaque auto-learning, and auto-apply roadmap mutations.

### Autonomy feedback board / knowledge-loop completion governance (new)

A new `autonomy_feedback` layer now tracks *post-emission* follow-up resolution status for campaigns.

- `autonomy_followup` still emits handoffs (`EMITTED`, `DUPLICATE_SKIPPED`).
- `autonomy_feedback` consumes emitted follow-ups and tracks downstream status (`PENDING`, `IN_PROGRESS`, `COMPLETED`, `BLOCKED`, `REJECTED`, `UNKNOWN`).
- manual-first run endpoint creates auditable resolution records, recommendation records, and summary counts for closed-loop governance.
- frontend route `/autonomy-feedback` exposes summary cards, candidate/resolution tracking, recommendation queue, and manual completion action.

Out of scope remains unchanged: real money, real broker/exchange execution, opaque auto-learning, and automatic roadmap/scenario apply.

### Autonomy insights board (new)

Added a formal `autonomy_insights` layer to synthesize reusable lessons across **closed lifecycle campaigns** (`closeout + followup + feedback`).

Capabilities:
- manual-first cross-campaign synthesis runs (`/api/autonomy-insights/run-review/`)
- auditable `CampaignInsight`, `InsightRecommendation`, and `InsightRun` records
- explicit success/failure/blocker/governance pattern extraction (rule-based, no ML/LLM authority)
- recommendation targets for memory/roadmap/scenario/program/manager/operator review
- frontend board at `/autonomy-insights` connected to cockpit, closeout, followup, feedback, and trace

Boundaries remain unchanged: local-first, single-user, paper/sandbox only, no real broker/exchange execution, and no opaque auto-apply to roadmap/scenario/policy/runtime.


### Autonomy advisory resolution board (new)

A new `autonomy_advisory_resolution` layer closes the governance-note loop after `autonomy_advisory` emission:

- consumes emitted advisory artifacts and tracks explicit downstream statuses (`PENDING`, `ACKNOWLEDGED`, `ADOPTED`, `DEFERRED`, `REJECTED`, `BLOCKED`, `CLOSED`)
- records auditable manual actions for acknowledge/adopt/defer/reject
- provides resolution runs, recommendation queue, and summary snapshots for cockpit/trace oriented operator review
- remains manual-first and recommendation-first (no opaque auto-apply to roadmap/scenario/program/manager)

Explicit non-goals remain unchanged: no real money, no broker/exchange execution, no black-box planner, and no multi-user enterprise orchestration.

### Autonomy backlog board / future-cycle planning handoff (new)

Added `autonomy_backlog` as a formal bridge between `autonomy_advisory_resolution` and future governance cycles.

What it adds:
- consumes `ADOPTED` / `ACKNOWLEDGED` advisory resolutions as backlog candidates
- creates auditable `GovernanceBacklogItem` records (roadmap/scenario/program/manager/operator_review targets)
- stores run and recommendation artifacts (`BacklogRun`, `BacklogRecommendation`) with explicit counts and rationale
- applies deterministic dedup + transparent priority heuristics (no ML and no black-box planner)
- keeps actions manual-first (`run-review`, `create`, `prioritize`, optional `defer`)

Hard boundaries:
- no auto-apply mutations to roadmap/scenario/program/manager
- no real-money execution and no live broker/exchange routing
- local-first, single-user, paper/sandbox only


## Autonomy intake board (new)

`autonomy_intake` adds a governed handoff between `autonomy_backlog` and planning surfaces.
It consumes READY/PRIORITIZED backlog items and emits auditable planning proposals (roadmap/scenario/program/manager/operator review) with manual-first controls and duplicate protection, without auto-applying downstream changes.

## autonomy_planning_review: governed planning adoption tracker (new)

`autonomy_planning_review` extiende el flujo posterior a `autonomy_intake` para cerrar el loop de handoff de planning proposals emitidas.

Qué hace:
- consume `PlanningProposal` ya emitidas
- registra resolución posterior (`PENDING`, `ACKNOWLEDGED`, `ACCEPTED`, `DEFERRED`, `REJECTED`, `BLOCKED`, `CLOSED`)
- genera runs y recomendaciones auditables para revisión manual

Qué **no** hace:
- no auto-aplica roadmap/scenario/program/manager
- no ejecuta broker/exchange real
- no introduce planner black-box

## autonomy_decision: accepted proposal registry and decision packages (new)

`autonomy_decision` añade la capa formal posterior a `autonomy_planning_review` para convertir proposals `ACCEPTED` en decisiones persistidas y auditables para el siguiente ciclo.

Qué hace:
- consume `PlanningProposalResolution` en estado `ACCEPTED`
- genera candidatos, recomendaciones y runs auditables de decisión
- registra `GovernanceDecision` por destino (`roadmap`, `scenario`, `program`, `manager`, `operator_review`)
- mantiene trazabilidad proposal/backlog/advisory/insight/campaign y links a trace
- mantiene manual-first (sin auto-apply en módulos destino)

Fuera de alcance:
- dinero real / broker-exchange real
- auto-apply opaco a roadmap/scenario/program/manager
- planner black-box / multiusuario enterprise

## autonomy_package: decision bundle registry and next-cycle planning seeds (new)

`autonomy_package` extiende el loop `autonomy_decision` con una capa de bundles explícitos y auditables para reutilizar decisiones formales en el siguiente ciclo de planificación.

- consume `GovernanceDecision` ya `REGISTERED/ACKNOWLEDGED`
- agrupa decisiones relacionadas por `target_scope + grouping_key`
- evita duplicados con dedupe explícito
- persiste `GovernancePackage`, `PackageRun`, `PackageRecommendation`
- mantiene un flujo `manual-first` y `recommendation-first`
- **no** auto-aplica cambios a roadmap/scenario/program/manager
- **no** agrega ejecución real broker/exchange

Ruta UI: `/autonomy-package`.
API base: `/api/autonomy-package/*`.

## Autonomy package review board (new)

Added `autonomy_package_review` as a formal post-registration governance layer.

- consumes already registered `GovernancePackage` rows from `autonomy_package`
- tracks downstream states: `PENDING`, `ACKNOWLEDGED`, `ADOPTED`, `DEFERRED`, `REJECTED`, `BLOCKED`, `CLOSED`
- emits manual-first recommendations (`ACKNOWLEDGE_PACKAGE`, `MARK_PACKAGE_ADOPTED`, etc.)
- closes the package handoff loop with auditable run history and resolution records
- keeps strict boundaries: no real money, no broker/exchange live execution, no opaque auto-apply into roadmap/scenario/program/manager

### Autonomy seed board / adopted package registry (new)

A new `autonomy_seed` layer now turns `autonomy_package_review` outcomes in `ADOPTED` state into explicit, auditable next-cycle planning seeds:

- consumes `PackageResolution` from `/api/autonomy-package-review/*`
- creates persistent `GovernanceSeed` artifacts (manual-first registration)
- stores recommendation-first `SeedRun` and `SeedRecommendation` audit trails
- classifies destination scope (`roadmap`, `scenario`, `program`, `manager`, `operator_review`) without auto-mutating those modules
- keeps full trace continuity from package/decision lineage into registered seed artifacts

Out of scope remains unchanged: no real money, no real broker/exchange execution, and no opaque auto-apply planner behavior.

### Autonomy seed review board / seed resolution tracker (new)

The stack now includes a dedicated `autonomy_seed_review` layer (`/api/autonomy-seed-review/*` + `/autonomy-seed-review`) that closes the post-registration governance loop for next-cycle seeds.

- consumes already-registered `autonomy_seed.GovernanceSeed` artifacts
- records auditable downstream resolution states (`ACKNOWLEDGED`, `ACCEPTED`, `DEFERRED`, `REJECTED`, etc.)
- emits recommendation-first review guidance and run snapshots
- keeps seed adoption manual-first (no opaque auto-apply into roadmap/scenario/program/manager)

Out of scope remains explicit: no real-money execution, no broker/exchange live routing, and no black-box planner authority.

### Scan agent filter hardening (new)

A new **scan agent filter layer** now hardens narrative intake before research triage and prediction context:

- endpoint family under `/api/scan-agent/*`
- parallel source consolidation for RSS + Reddit + optional X/Twitter adapters (read-only)
- explicit deduplication + narrative clustering
- transparent signal scoring (`novelty`, `intensity`, `source_confidence`, `market_divergence`, `total_signal_score`)
- recommendation-first handoff (`SEND_TO_RESEARCH_TRIAGE`, `SEND_TO_PREDICTION_CONTEXT`, `KEEP_ON_WATCHLIST`, `IGNORE_NOISE`, `REQUIRE_MANUAL_REVIEW`)
- fully auditable run artifacts (`SourceScanRun`, `NarrativeSignal`, `NarrativeCluster`, `ScanRecommendation`)

This layer strengthens `research_agent` scan/filter quality but does **not** replace research triage/pursuit authority and does **not** introduce real-money or auto-execution behavior.


## Research Agent scan hardening (market universe triage)

- Added a hardened `/api/research-agent/*` layer for read-only market universe triage with explicit structural filtering, transparent pursue-worthiness scoring, and recommendation-first outputs.
- New auditable entities: `MarketUniverseRun`, `MarketResearchCandidate`, `MarketTriageDecisionV2`, `MarketResearchRecommendation`.
- The scan-agent remains upstream for narrative dedup/clustering/signals; research-agent consumes those signals as context (not as sole authority).
- Scope remains local-first, manual-first, paper/sandbox-only, and read-only toward providers.

### Risk agent runtime hardening / sizing governance / paper watch board (new)

`risk_agent` now includes a stronger runtime layer between `prediction_agent` assessments and downstream paper execution simulation.

What is now formalized:
- run-level audit record (`RiskRuntimeRun`)
- candidate intake from prediction runtime (`RiskRuntimeCandidate`)
- explicit approval gate (`RiskApprovalDecision`: APPROVED / APPROVED_REDUCED / BLOCKED / NEEDS_REVIEW)
- conservative sizing plan (`RiskSizingPlan`: bounded/capped fractions, paper risk budget)
- explicit post-entry watch board (`PositionWatchPlan`)
- recommendation-first handoff objects (`RiskRuntimeRecommendation`)

API surface:
- `POST /api/risk-agent/run-runtime-review/`
- `GET /api/risk-agent/runtime-candidates/`
- `GET /api/risk-agent/approval-decisions/`
- `GET /api/risk-agent/sizing-plans/`
- `GET /api/risk-agent/watch-plans/`
- `GET /api/risk-agent/runtime-recommendations/`
- `GET /api/risk-agent/runtime-summary/`

Scope unchanged:
- local-first, single-user, manual-first
- paper/sandbox only
- no real-money execution
- no live broker/exchange execution

### Postmortem learning loop hardening (new)

The `learning_memory` layer now includes a stronger **postmortem → learning** loop focused on auditable, conservative, manual-first learning reuse.

New capabilities:
- `PostmortemLearningRun` audit trail per loop execution.
- formal `FailurePattern` registry (ACTIVE/WATCH/EXPIRED/NEEDS_REVIEW).
- bounded `PostmortemLearningAdjustment` records (PROPOSED/ACTIVE/PAUSED/EXPIRED/REJECTED).
- explicit `LearningApplicationRecord` entries for downstream influence visibility.
- recommendation-first `LearningRecommendation` outputs (`ACTIVATE_ADJUSTMENT`, `KEEP_ADJUSTMENT_ON_WATCH`, `EXPIRE_ADJUSTMENT`, `REQUIRE_MANUAL_LEARNING_REVIEW`, etc.).

API:
- `POST /api/learning/run-postmortem-loop/`
- `GET /api/learning/failure-patterns/`
- `GET /api/learning/adjustments/`
- `GET /api/learning/application-records/`
- `GET /api/learning/recommendations/`
- `GET /api/learning/postmortem-loop-summary/`

Scope remains unchanged:
- local-first, single-user, paper/sandbox only
- no real money / no broker live execution
- no opaque autonomous learning authority
- no automatic model retraining

### Opportunity cycle runtime hardening (new)

A new auditable runtime layer is now available at `/api/opportunity-cycle/*` and `/opportunity-cycle`.

- Consolidates upstream outputs from `research_agent`, `prediction_agent`, `risk_agent`, and `learning_memory` into fused opportunity assessments.
- Emits explicit statuses (`READY_FOR_PROPOSAL`, `WATCH_ONLY`, `BLOCKED_BY_RISK`, `BLOCKED_BY_LEARNING`, `LOW_CONVICTION`, `NEEDS_REVIEW`).
- Creates paper proposal handoffs and recommendation-first downstream actions (`SEND_TO_PROPOSAL_ENGINE`, `SEND_TO_EXECUTION_SIMULATOR`, watch/block/manual-review outcomes).
- Preserves local-first, manual-first, paper-only boundaries.

Out of scope remains unchanged: no broker/exchange live execution, no real-money trading, and no opaque auto-apply planner.


## Quantitative evaluation runtime hardening (2026-03-30)

- Added an auditable ex-post runtime evaluation layer under `evaluation_lab` that links resolved outcomes with prediction, risk, opportunity-fusion, and paper proposal artifacts.
- Added calibration buckets, effectiveness metrics, drift flags, and explicit human recommendations (manual-first, no auto-tuning/no auto-retraining).
- Added API endpoints under `/api/evaluation/*` for runtime evaluation execution and board data retrieval.
- Strengthened `/evaluation` frontend with outcome-alignment, calibration, effectiveness, recommendations, and manual trigger UX.
- Scope remains local-first, single-user, paper/sandbox only; no real-money execution or silent policy/model mutation.


## Governed tuning board (manual quantitative improvement loop)

The platform now includes a dedicated `tuning_board` layer (`/api/tuning/*` + `/tuning`) that converts `evaluation_lab` metrics/drift findings into explicit, bounded, reviewable tuning proposals.

- consumes `EvaluationRuntimeRun`, `EffectivenessMetric`, `CalibrationBucket`, and `EvaluationRecommendation` evidence
- emits auditable `TuningReviewRun`, `TuningProposal`, `TuningImpactHypothesis`, `TuningRecommendation`, and optional `TuningProposalBundle` records
- preserves metric -> recommendation -> proposal traceability and scoped targeting (global/provider/category/horizon/model_mode)
- integrates conceptually with `trust_calibration`, `policy_tuning`, `experiments`, `champion_challenger`, and `promotion_committee` without deep auto-integration in this step
- keeps strict manual-first governance: **no auto-tuning, no silent threshold mutation, no auto-retraining, no live-money execution**

Primary endpoints:
- `POST /api/tuning/run-review/`
- `GET /api/tuning/proposals/`
- `GET /api/tuning/hypotheses/`
- `GET /api/tuning/recommendations/`
- `GET /api/tuning/summary/`
- `GET /api/tuning/bundles/` (optional grouping panel)

### Promotion manual adoption action board / approved-change executor (new)

`promotion_committee` now includes a formal **manual adoption action** layer between approval and any paper/demo change execution:

- consumes `PromotionCase` items in `APPROVED_FOR_MANUAL_ADOPTION`
- resolves target mapping (`policy_tuning`, `trust_calibration`, stack binding, or rollout handoff)
- creates auditable manual actions with before/after snapshots
- prepares rollback plans when risk or scope requires it
- supports explicit operator apply records only (`POST /api/promotion/apply/<case_id>/`)
- never auto-applies, never runs live execution, never auto-promotes

New API endpoints:
- `POST /api/promotion/run-adoption-review/`
- `GET /api/promotion/adoption-candidates/`
- `GET /api/promotion/adoption-actions/`
- `GET /api/promotion/rollback-plans/`
- `GET /api/promotion/adoption-recommendations/`
- `GET /api/promotion/adoption-summary/`
- `POST /api/promotion/apply/<case_id>/`

This closes the governance gap: **approved case → explicit manual action → optional rollout handoff / rollback-ready record**.

## Rollout execution prep board / safe manual rollback control (2026-03-30)

A new rollout-preparation layer is now available under `promotion_committee` to bridge:

`approved case -> manual adoption action -> rollout prep -> manual rollout / manual rollback`.

What it adds:
- auditable `RolloutPreparationRun`
- `RolloutActionCandidate` built from existing `ManualAdoptionAction`
- `ManualRolloutPlan` with staged steps + monitoring intent
- `RolloutCheckpointPlan` for pre/post/risk/calibration/drift/rollback checks
- `ManualRollbackExecution` for explicit rollback execution logging
- `RolloutPreparationRecommendation` for conservative operator guidance

API endpoints:
- `POST /api/promotion/run-rollout-prep/`
- `GET /api/promotion/rollout-candidates/`
- `GET /api/promotion/rollout-plans/`
- `GET /api/promotion/checkpoint-plans/`
- `GET /api/promotion/rollback-executions/`
- `GET /api/promotion/rollout-recommendations/`
- `GET /api/promotion/rollout-summary/`
- `POST /api/promotion/prepare-rollout/<case_id>/`
- `POST /api/promotion/rollback/<action_id>/`

Boundary remains strict:
- no auto-rollout
- no auto-apply
- no live trading / real money
- manual-first, local-first, paper/sandbox-only.

### Manual rollout execution board / checkpoint outcome control (new)

`promotion_committee` now includes a post-preparation manual execution loop for rollout governance:

- consumes existing `ManualRolloutPlan` + `RolloutCheckpointPlan` (no duplication of rollout prep)
- creates auditable execution entities: `RolloutExecutionRun`, `RolloutExecutionRecord`, `CheckpointOutcomeRecord`, `PostRolloutStatus`, `RolloutExecutionRecommendation`
- adds explicit API surface for manual execution review, execute, checkpoint outcome recording, and manual close
- keeps all decisions manual-first, paper-only, local-first, and reversible
- treats evaluation/risk/trust/policy signals as bounded context only (no auto-rollout, no silent auto-rollback)

New API endpoints:
- `POST /api/promotion/run-rollout-execution/`
- `GET /api/promotion/rollout-executions/`
- `GET /api/promotion/checkpoint-outcomes/`
- `GET /api/promotion/post-rollout-status/`
- `GET /api/promotion/rollout-execution-recommendations/`
- `GET /api/promotion/rollout-execution-summary/`
- `POST /api/promotion/execute-rollout/<plan_id>/`
- `POST /api/promotion/record-checkpoint-outcome/<checkpoint_id>/`
- `POST /api/promotion/close-rollout/<execution_id>/`

### Post-rollout certification board / stabilization gate (new)

The platform now includes a formal post-rollout certification layer in `certification_board` that closes the gap between rollout execution and baseline confirmation:

- rollout execution evidence is consumed (not duplicated)
- stabilization candidates + evidence packs + decisions + recommendations are persisted and auditable
- outputs classify changes as:
  - certified for paper baseline
  - kept under observation
  - manual review required
  - rollback recommended / reject certification
- no automatic baseline switch, no auto-promote, no live/real-money behavior

Primary API:
- `POST /api/certification/run-post-rollout-review/`
- `GET /api/certification/candidates/`
- `GET /api/certification/evidence-packs/`
- `GET /api/certification/decisions/`
- `GET /api/certification/recommendations/`
- `GET /api/certification/post-rollout-summary/`

## Paper baseline confirmation board / certified-change adoption registry (2026-03-30)

A formal baseline-confirmation layer now sits on top of `certification_board` so certified changes do **not** silently become active paper baselines.

New auditable entities:
- `BaselineConfirmationRun`
- `BaselineConfirmationCandidate`
- `PaperBaselineConfirmation`
- `BaselineBindingSnapshot`
- `BaselineConfirmationRecommendation`

New API surface (`/api/certification/*`):
- `POST /run-baseline-confirmation/`
- `GET /baseline-candidates/`
- `GET /baseline-confirmations/`
- `GET /binding-snapshots/`
- `GET /baseline-recommendations/`
- `GET /baseline-summary/`
- `POST /confirm-baseline/<decision_id>/`
- `POST /rollback-baseline/<confirmation_id>/` (manual rollback preparation)

Governance boundaries preserved:
- certification still decides certification status
- baseline confirmation is a separate **manual** operator step
- no auto-promote / no auto champion switch / no silent apply
- rollback path to previous baseline is explicitly captured
- local-first, single-user, paper/sandbox only


## Paper baseline activation board

The certification domain now includes a **paper baseline activation board** that sits after `PaperBaselineConfirmation=CONFIRMED`. It creates manual activation candidates, resolves active-binding replacement targets, records before/after snapshots, updates an explicit active paper binding registry, and keeps rollback reversible and auditable. This layer is manual-first, paper-only, local-first, and does not auto-switch champion, auto-promote, or execute live trading.

## Active baseline health board / degradation watch loop (new)

`certification_board` now includes a formal **active baseline health watch** loop after baseline activation.

It consumes `ActivePaperBindingRecord` and emits auditable:
- `BaselineHealthRun`
- `BaselineHealthCandidate`
- `BaselineHealthStatus`
- `BaselineHealthSignal`
- `BaselineHealthRecommendation`

API (`/api/certification`):
- `POST /run-baseline-health-review/`
- `GET /health-candidates/`
- `GET /health-status/`
- `GET /health-signals/`
- `GET /health-recommendations/`
- `GET /health-summary/`

Governance boundaries remain strict: no auto-deactivate baseline, no auto-retune, no auto-switch champion, no silent apply. This layer is recommendation-first, manual-first, local-first, paper-only.

## Baseline response board / health-to-retuning governance loop (new)

After `baseline health watch`, the platform now adds a formal `baseline response` layer in `certification_board`.

What it adds:
- explicit `BaselineResponseRun` audit records
- explicit `BaselineResponseCase` records per active baseline pressure
- `ResponseEvidencePack` for consolidated health/evaluation/risk/opportunity context
- `ResponseRoutingDecision` to downstream governance targets
- `BaselineResponseRecommendation` for manual next-step guidance

Manual-first guarantees:
- no auto-retune
- no auto-rollback
- no auto-deactivate
- no auto-promote/switch

API:
- `POST /api/certification/run-baseline-response-review/`
- `GET /api/certification/response-cases/`
- `GET /api/certification/response-evidence-packs/`
- `GET /api/certification/response-routing-decisions/`
- `GET /api/certification/response-recommendations/`
- `GET /api/certification/response-summary/`

## Baseline response actions/tracking loop

The `certification_board` flow now extends baseline response with an explicit manual handoff layer:

`response case -> routing action -> downstream tracking -> case closure`

This layer consumes existing baseline response outputs and records auditable manual routing/tracking artifacts without automatically creating or executing downstream reviews.

Key APIs include run/list/summary plus explicit manual actions: `route-response-case`, `update-response-tracking`, and `close-response-case` (manual closure without downstream action).

### Baseline downstream acknowledgement board / response review lifecycle (new)

The `certification_board` domain now extends baseline response actions with a formal downstream lifecycle layer:

- explicit downstream acknowledgement tracking (`SENT`, `ACKNOWLEDGED`, `ACCEPTED_FOR_REVIEW`, `WAITING_MORE_EVIDENCE`, `REJECTED_BY_TARGET`, `NO_RESPONSE`)
- granular review stages (`intake_review`, `evidence_collection`, `board_review`, `manual_followup`, `downstream_resolution`, `rejection_review`)
- explicit downstream lifecycle outcomes (`RESOLVED_BY_TARGET`, `REJECTED_BY_TARGET`, `WAITING_EVIDENCE`, etc.)
- lifecycle recommendations for manual follow-up and preparation of future formal case resolution

This layer is manual-first and auditable. It does **not** auto-open downstream board workflows and does **not** auto-resolve response cases.


### Baseline response resolution (Prompt 133 revised)
- Adds a formal manual-first layer after downstream lifecycle: resolution candidates, proposed case resolutions, downstream evidence references, and conservative closure recommendations.
- Keeps existing routing/tracking/lifecycle intact and does not auto-close cases. Final closure remains explicit via `POST /api/certification/resolve-response-case/<case_id>/`.
- New run/board endpoint: `POST /api/certification/run-baseline-response-resolution/` with list/summary endpoints for candidates, resolutions, references, and recommendations.
- Scope remains paper/sandbox only (no live trading, no auto-retune/rollback/deactivate/promote).

## Autonomous paper trade-cycle executor (Prompt 134)

A new `autonomous_trader` layer now runs a governed, paper-only autonomous mission loop with minimal human intervention:

- explicit cycle run audit (`AutonomousTradeCycleRun`) from candidate intake to outcome summary
- candidate consolidation from existing opportunity/research/prediction/risk context (`AutonomousTradeCandidate`)
- transparent decisioning (`WATCH`, `EXECUTE_PAPER_TRADE`, and explicit blocks/skips)
- paper execution linkage only (reuses `paper_trading` execution service; no live routing)
- automated watch records and outcome records with conservative postmortem/learning handoff flags
- backend API under `/api/autonomous-trader/*` and frontend route `/autonomous-trader`

Guardrails remain unchanged: runtime/policy/safety/certification still govern whether execution can proceed; this layer orchestrates and audits the cycle.

### Autonomous outcome handoff engine (new)

`autonomous_trader` now closes the paper-only post-trade loop with an explicit, auditable bridge:

- `AutonomousTradeOutcome` → `AutonomousPostmortemHandoff` → `AutonomousLearningHandoff`
- new run envelope: `AutonomousOutcomeHandoffRun`
- transparent decision records: `AutonomousOutcomeHandoffRecommendation`
- strict dedupe and blocker handling to avoid infinite re-emission
- integration reuses existing authorities:
  - `postmortem_agents` / `postmortem_demo` for postmortem board activation
  - `learning_memory` for conservative learning capture

New endpoints:
- `POST /api/autonomous-trader/run-outcome-handoff/`
- `GET /api/autonomous-trader/outcome-handoff-runs/`
- `GET /api/autonomous-trader/postmortem-handoffs/`
- `GET /api/autonomous-trader/learning-handoffs/`
- `GET /api/autonomous-trader/outcome-handoff-recommendations/`
- `GET /api/autonomous-trader/outcome-handoff-summary/`

Boundaries remain unchanged: local-first, single-user, paper/sandbox only, no real money, no live broker/exchange routing, no auto-retune/auto-promote.

### Autonomous feedback reuse bridge (new)

`autonomous_trader` now includes a conservative **learning-informed next-cycle feedback reuse bridge** that connects:
- `postmortem_board` outcomes and handoff lineage
- `learning_memory` adjustments and lessons
- `memory_retrieval` precedent retrieval

into the next autonomous paper cycle.

What it adds:
- auditable feedback reuse run records
- candidate-level retrieved learning contexts
- bounded influence records (context/caution/confidence reduction/repeat-pattern block)
- explicit recommendations and summary telemetry
- `/autonomous-trader` UI section: **Learning & Feedback Reuse**

Guardrails stay unchanged:
- paper/sandbox only
- no real money, no real broker routing
- no auto-retune, no auto-promote, no opaque model switching
- risk/policy/safety remain final authority boundaries

### Autonomous Kelly sizing bridge (new)

`autonomous_trader` now includes a conservative, auditable paper-sizing bridge that links prediction, risk, portfolio governor, allocation context, and feedback reuse before execution.

- bounded/fractional Kelly-informed sizing only (no aggressive Kelly)
- explicit context -> decision -> recommendation traceability
- portfolio-aware and risk-first discounts/caps
- execution now consumes sizing decision notional/quantity for paper trades
- remains strictly local-first, single-user, paper/sandbox only (no live routing, no real money)

<<<<<<< HEAD
### Scan→Research intelligence handoff hardening (new)

The scan layer now includes an explicit, auditable narrative-consensus handoff before research triage:

- cross-source consensus/conflict clustering over RSS + Reddit + X/Twitter scan signals
- narrative-vs-market divergence scoring
- research handoff priority buckets/statuses with explicit reason codes
- conservative recommendation outputs (send/watchlist/defer/block/manual-review)
- traceability chain: `signals -> cluster -> consensus -> divergence -> handoff priority -> recommendation`

API additions under `/api/scan-agent/`:
- `POST run-consensus-review/`
- `GET consensus-runs/`
- `GET consensus-records/`
- `GET market-divergence-records/`
- `GET research-handoff-priorities/`
- `GET consensus-recommendations/`
- `GET consensus-summary/`

This remains local-first, single-user, paper/sandbox only, and does **not** replace `research_agent` formal triage authority.
=======

## Autonomous position watch hardening (paper-only)
- Adds a post-entry autonomous watch loop for open paper positions with explicit HOLD/REDUCE/CLOSE/REVIEW_REQUIRED decisions.
- Uses sentiment/narrative drift, risk posture, and portfolio pressure as inputs while keeping risk/policy/runtime/safety as authorities.
- Executes only paper reduce/close actions with auditable lineage records; no real broker routing and no real money.
>>>>>>> origin/main

### Research pursuit scoring hardening (new)

`research_agent` now includes an explicit structural triage + pursuit scoring + prediction-handoff bridge:

- consumes `ResearchHandoffPriority` from scan→research consensus/divergence output
- performs structural assessment (liquidity, volume, time window, activity)
- computes transparent pursuit-worthiness components (no opaque black-box ranking)
- emits prediction-handoff candidates (`READY`/`WATCH`/`DEFERRED`/`BLOCKED`) with reason codes
- stores auditable recommendations and run summaries for `/research-agent`

Boundaries remain unchanged: local-first, single-user, paper/sandbox only, no live execution, and `prediction_agent` remains probability/edge authority.

### Prediction intake hardening / calibrated conviction review / risk-ready handoff (new)

`prediction_agent` now includes an explicit intake bridge that consumes `PredictionHandoffCandidate` from `research_agent` and produces a smaller, auditable prediction set before `risk_agent`:

- `PredictionIntakeRun`
- `PredictionIntakeCandidate`
- `PredictionConvictionReview`
- `RiskReadyPredictionHandoff`
- `PredictionIntakeRecommendation`

Pipeline:
`PredictionHandoffCandidate` → intake statusing → calibrated conviction review (probability/edge/confidence/uncertainty) → risk-ready handoff.

Boundaries remain unchanged:
- paper/sandbox only
- no live broker/exchange execution
- no real money
- `risk_agent` remains final authority for approval/posture/sizing/watch.


### Risk intake hardening / approval+sizing-watch bridge / autonomous readiness (new)

`risk_agent` now consumes `RiskReadyPredictionHandoff` directly and builds an auditable prediction→risk→autonomous bridge for paper-mode only:

- `RiskRuntimeRun` now tracks handoffs considered, approval split (`APPROVED`, `APPROVED_REDUCED`, `BLOCKED`, `NEEDS_REVIEW`) and execution-ready counts.
- Intake entities now preserve prediction conviction, uncertainty, portfolio pressure, and reason codes before approval.
- Approval review feeds sizing + watch plans and emits explicit `AutonomousExecutionReadiness` states (`READY`, `READY_REDUCED`, `WATCH_ONLY`, `BLOCKED`, `DEFERRED`).
- Recommendation output is now intake/readiness-aware (`APPROVE_FOR_AUTONOMOUS_EXECUTION`, `APPROVE_WITH_REDUCED_SIZE`, `BLOCK_FOR_RISK_POSTURE`, etc.).

Scope remains unchanged: local-first, single-user, paper/sandbox-only, no real money, no broker/exchange execution, and no replacement of policy/safety/runtime/autonomous governance authorities.

### Autonomous execution intake hardening / readiness-driven dispatch bridge (new)

`autonomous_trader` now includes a formal execution-intake bridge that consumes `risk_agent.AutonomousExecutionReadiness` before paper dispatch.

Added auditable entities:
- `AutonomousExecutionIntakeRun`
- `AutonomousExecutionIntakeCandidate`
- `AutonomousExecutionDecision`
- `AutonomousDispatchRecord`
- `AutonomousExecutionRecommendation`

Bridge flow:
`AutonomousExecutionReadiness` → intake candidate → explicit decision (`EXECUTE_NOW`, `EXECUTE_REDUCED`, `KEEP_ON_WATCH`, `DEFER`, `BLOCK`, `REQUIRE_MANUAL_REVIEW`) → paper-only dispatch record.

Boundaries remain unchanged: local-first, single-user, paper/sandbox only, no real money, no live broker/exchange routing, and no bypass of risk/policy/runtime/safety/certification authorities.


## Mission Control Autonomous Runtime Loop
- New governed autonomous runtime loop orchestration is available under `/api/mission-control/run-autonomous-runtime/` and related autonomous runtime list/summary endpoints.
- This layer is paper-only, local-first, and single-user. It orchestrates cycle plan → execution → outcome → recommendation without replacing `autonomous_trader` operational authority.
- It reinforces runtime/safety/portfolio guardrails and supports reduced or blocked cycles rather than forcing execution.

## Autonomous session timing policy (Prompt 147)

The project now includes a configurable **session timing policy** layer under mission control to improve autonomous cadence governance.

- Local-first, single-user, paper/sandbox-only behavior remains unchanged.
- Heartbeat runner is extended (not replaced) with explicit timing decisions and `next_due_at` traceability.
- Timing policy supports schedule profiles, quiet-window handling, cooldown-aware waits, and conservative pause/stop recommendations.
- No live broker/exchange execution, no real-money flows, and no enterprise distributed scheduler were added.

### Adaptive session profile controller (new)

`mission_control` ahora incluye una capa explícita y auditable de **adaptive session profile control**:

- flujo: `session context -> context review -> switch decision -> switch record -> timing behavior`
- entidades auditables:
  - `AutonomousProfileSelectionRun`
  - `AutonomousSessionContextReview`
  - `AutonomousProfileSwitchDecision`
  - `AutonomousProfileSwitchRecord`
  - `AutonomousProfileRecommendation`
- switching conservador entre perfiles (`balanced_local`, `conservative_quiet`, `monitor_heavy`) con hysteresis para evitar oscilaciones.
- integración directa con heartbeat local y timing policy existente (no reemplazo).

Boundaries se mantienen: local-first, single-user, paper/sandbox only, sin broker/exchange real, sin live execution, sin dinero real, sin planner black-box.

## Global Session Admission Controller (Prompt 151)

Mission control now includes an explicit **global session admission** layer that coordinates how many autonomous runtime sessions can stay active at once and which sessions should be admitted, resumed, parked, deferred, paused, or retired.

- Local-first and single-user oriented.
- Paper/sandbox only (no live broker/exchange routing, no real money).
- Conservative, auditable, and portfolio-aware.
- Extends (does not replace) portfolio governor, runtime governor, safety guard, session timing, session health, and recovery governance.


### Global exposure harmonizer / cross-session conflict resolution (new)

`portfolio_governor` now includes an explicit **Global Exposure Coordination** layer for paper-only operation:

- pipeline: admitted sessions + open positions + pending dispatches → exposure clustering → conflict review → throttle/defer/park/pause/manual-review decisions → auditable recommendations.
- new auditable entities:
  - `PortfolioExposureCoordinationRun`
  - `PortfolioExposureClusterSnapshot`
  - `SessionExposureContribution`
  - `PortfolioExposureConflictReview`
  - `PortfolioExposureDecision`
  - `PortfolioExposureRecommendation`
- conservative API surface:
  - `POST /api/portfolio-governor/run-exposure-coordination-review/`
  - `GET /api/portfolio-governor/exposure-coordination-runs/`
  - `GET /api/portfolio-governor/exposure-cluster-snapshots/`
  - `GET /api/portfolio-governor/session-exposure-contributions/`
  - `GET /api/portfolio-governor/exposure-conflict-reviews/`
  - `GET /api/portfolio-governor/exposure-decisions/`
  - `GET /api/portfolio-governor/exposure-recommendations/`
  - `GET /api/portfolio-governor/exposure-coordination-summary/`

This layer extends existing portfolio/risk/runtime/safety authorities and does **not** replace admission control, timing policy, or mission control governance.

### Portfolio exposure apply bridge / runtime enforcement (new)

`portfolio_governor` now includes an explicit **exposure decision apply bridge**:

- pipeline: `exposure decision -> apply targets -> apply decision -> apply record -> runtime effect`
- conservative runtime effects only (paper-only):
  - throttle new entries at cluster/admission gate level
  - defer pending dispatches safely
  - park weaker runtime sessions
  - pause cluster activity conservatively
  - manual-review-only fallback for ambiguous cases
- full audit entities:
  - `PortfolioExposureApplyRun`
  - `PortfolioExposureApplyTarget`
  - `PortfolioExposureApplyDecision`
  - `PortfolioExposureApplyRecord`
  - `PortfolioExposureApplyRecommendation`

Boundary guarantees remain strict: local-first, single-user, paper/sandbox only, no live broker/exchange execution, no real money, and no aggressive auto-closing of open positions.

### Global runtime posture controller / operating mode (new)

`runtime_governor` now includes an explicit, auditable **global operating mode** layer for paper runtime coordination:

- posture pipeline: `global context -> posture snapshot -> mode decision -> switch record -> recommendation`
- conservative modes: `BALANCED`, `CAUTION`, `MONITOR_ONLY`, `RECOVERY_MODE`, `THROTTLED`, `BLOCKED`
- transparent (non-LLM, non-black-box) switching with simple hysteresis to reduce oscillation
- local-first, single-user, paper-only boundaries remain strict
- no live broker execution, no real money, no replacement of runtime/safety/portfolio/mission-control authorities

API:
- `POST /api/runtime-governor/run-operating-mode-review/`
- `GET /api/runtime-governor/runtime-posture-runs/`
- `GET /api/runtime-governor/runtime-posture-snapshots/`
- `GET /api/runtime-governor/operating-mode-decisions/`
- `GET /api/runtime-governor/operating-mode-switch-records/`
- `GET /api/runtime-governor/operating-mode-recommendations/`
- `GET /api/runtime-governor/operating-mode-summary/`
- `POST /api/runtime-governor/apply-operating-mode/<decision_id>/`

## Global mode enforcement bridge (Prompt 155)
- Runtime governor now runs an explicit downstream mode-enforcement review to make global mode operational (not only descriptive).
- Enforcement remains local-first, single-user, paper/sandbox only (no real money, no live broker routing).
- The bridge adds auditable run/module impact/decision/recommendation records and summary endpoints for runtime/mission-control visibility.

## Runtime tuning drift diff observability (Prompt 169)

`runtime_governor` now exposes a read-only tuning snapshot diff layer so operators can inspect exactly what changed per scope/snapshot.

- API: `GET /api/runtime-governor/tuning-context-diffs/` and `GET /api/runtime-governor/tuning-context-diffs/<snapshot_id>/`
- Diff payload includes field-level `changed_fields`, optional `unchanged_fields`, and `diff_summary`.
- Comparison is snapshot-to-previous-snapshot within the same `source_scope`.
- Scope remains unchanged: paper-only, no live trading, no authority replacement, and no operational tuning behavior change.

## Runtime tuning run correlation observability (Prompt 171)

`runtime_governor` now adds a read-only correlation layer to link runtime runs with tuning context snapshots/fingerprints.

- API: `GET /api/runtime-governor/tuning-run-correlations/`
- Supports query params: `source_scope`, `latest_only`, `limit`
- Correlates at least: runtime feedback, operating mode, mode stabilization, and mode enforcement runs
- Returns readable summary rows with `source_scope`, `source_run_id`, tuning snapshot/profile/fingerprint, drift status, and optional run timestamp

This is strictly observability/debugging for cross-run traceability. It does not modify operational logic, does not add live trading paths, and remains paper-only.

## Runtime tuning scope digest (read-only)

Se agregó una capa compacta de observabilidad en `runtime_governor` para resumir el estado actual de tuning por `source_scope` usando los últimos snapshots, drift y correlación de run disponibles.

- Endpoint: `GET /api/runtime-governor/tuning-scope-digest/` (opcional `source_scope`)
- Campos clave por scope: snapshot más reciente, run correlacionado (si existe), profile/fingerprint, drift status y `digest_summary` legible.

Esta capa es **solo lectura**, mantiene el sistema en **paper-only**, no cambia lógica operativa ni reemplaza authorities existentes.

## Runtime tuning latest-diff quick navigation (Prompt 175)

`runtime_governor` now exposes explicit per-scope links to the latest comparable tuning diff so operators can jump from digest/alerts to drill-down faster.

- Extended endpoints:
  - `GET /api/runtime-governor/tuning-scope-digest/`
  - `GET /api/runtime-governor/tuning-change-alerts/`
- New optional fields:
  - `latest_diff_snapshot_id`
  - `latest_diff_status`
  - `latest_diff_summary`
- If a scope has no previous snapshot to compare against, these fields return explicit `null`.
- Runtime UI `/runtime` adds a simple **View latest diff** action in Scope Digest and Change Alerts, reusing existing diff detail API.

This is navigation/read-only usability only: no new authority, no live trading, no real money, no operational logic changes.

## Runtime tuning alert summary board (Prompt 174)

`runtime_governor` now adds a compact, attention-first summary layer on top of existing tuning change alerts.

- Endpoint: `GET /api/runtime-governor/tuning-change-alert-summary/` (optional `source_scope`)
- Purpose: summarize counts (`STABLE`, `MINOR_CHANGE`, `PROFILE_SHIFT`, `REVIEW_NOW`), provide attention-first scope ordering, and show highest-priority / most-recent changed scope.
- Runtime UI: `/runtime` now includes a **Tuning Alert Summary** section (cards + ordered review list) without creating a new page.

This addition is read-only, paper-only, and does not auto-apply anything or alter operational runtime behavior.

### Runtime Tuning Review Board (new)

`runtime_governor` now includes a compact read-only **Runtime Tuning Review Board** in `/runtime` so operators can prioritize scope review quickly without changing operational logic.

- API:
  - `GET /api/runtime-governor/tuning-review-board/`
    - optional query params: `source_scope`, `attention_only=true|false`, `limit`
  - `GET /api/runtime-governor/tuning-review-board/<source_scope>/`
- Behavior:
  - deterministic priority order: `REVIEW_NOW > PROFILE_SHIFT > MINOR_CHANGE > STABLE`
  - intra-priority ordering by guardrail changes, field changes, recency, and stable scope tiebreak
  - fast navigation to latest diff and correlated run context
  - runtime focus by query param: `/runtime?tuningScope=<source_scope>`
- Boundaries:
  - strictly read-only, paper-only, local-first
  - no new operational mutations
  - no authority changes

## Runtime Tuning Investigation Packet (new)

Runtime governor now exposes a compact **read-only investigation packet** per `source_scope` to unify review board priority, diff preview, and correlated run context in one reusable payload:

- Endpoint: `GET /api/runtime-governor/tuning-investigation/<source_scope>/`
- Runtime handoff link supports auto-open investigation view:
  - `/runtime?tuningScope=<source_scope>&investigate=1`
- Packet includes summary, reason codes, compact diff preview (max 5 fields + remaining counts), correlated run context (or explicit nulls), and runtime deep links.

This remains observability-only, paper-only, and does not change runtime/tuning operational logic.

## Runtime tuning scope timeline (Prompt 180)

`runtime_governor` now exposes a compact read-only **Runtime Tuning Scope Timeline** per `source_scope` to add short recent-history context on top of investigation.

- Endpoint: `GET /api/runtime-governor/tuning-scope-timeline/<source_scope>/`
- Query params:
  - `limit` (default `5`)
  - `include_stable` (default `true`)
- Returns deterministic timeline summary + flags (`is_recently_stable`, `has_recent_profile_shift`, `has_recent_review_now`) and compact entries (snapshot metadata, drift/alert, label/reason codes, diff summary/counts, correlated run info).

This is read-only/paper-only observability. No new persistent model, no mutative endpoint, and no runtime/tuning operational behavior changes.

UI integration lives in `/runtime` inside existing **Tuning Investigation** as **Recent Scope Timeline** (with light toggles: non-stable only + short/long recent history). Cockpit was not expanded in this prompt.

### Cockpit recent scope timeline strip (Prompt 181)

`/cockpit` compact tuning investigation now also shows a compact **Recent Timeline** strip by reusing the existing read-only endpoint `GET /api/runtime-governor/tuning-scope-timeline/<source_scope>/` (small default limit, non-stable toggle, and show-more expansion). Full investigation stays in `/runtime?tuningScope=<scope>&investigate=1`. No new models/endpoints or operational logic changes were added (paper-only/read-only).


### Runtime tuning manual review state (new)

`runtime_governor` now includes a compact **manual review state** layer for tuning scopes (`source_scope`) to track operator review intent without changing operational runtime logic:

- statuses: `UNREVIEWED`, `ACKNOWLEDGED_CURRENT`, `FOLLOWUP_REQUIRED`, `STALE_REVIEW`
- manual actions:
  - `POST /api/runtime-governor/acknowledge-tuning-scope/<source_scope>/`
  - `POST /api/runtime-governor/mark-tuning-scope-followup/<source_scope>/`
  - `POST /api/runtime-governor/clear-tuning-scope-review/<source_scope>/`
- read/audit:
  - `GET /api/runtime-governor/tuning-review-state/`
  - `GET /api/runtime-governor/tuning-review-state/<source_scope>/`
  - `GET /api/runtime-governor/tuning-review-actions/`

Stale detection is automatic and non-destructive: if a newer tuning snapshot appears after a reviewed snapshot, the effective status is exposed as `STALE_REVIEW` at read time.

Scope remains paper-only and observability-first; this does not alter runtime/tuning decision logic.

`/cockpit` now also consumes this layer inside **Runtime Tuning Attention**:
- per-scope manual-review badge/summary based on `effective_review_status` (`UNREVIEWED`, `ACKNOWLEDGED`, `FOLLOWUP`, `STALE`)
- compact investigation block **Manual Review** (status, summary, last action, stale indicator)
- inline manual actions that reuse existing endpoints (`Acknowledge current`, `Mark follow-up`, `Clear review state`)
- full handoff remains `/runtime?tuningScope=<scope>&investigate=1`

No operational runtime/tuning behavior changed; this is still paper-only operator UX.

### Runtime Tuning Human Review Queue (Prompt 184)

A new read-only runtime-governor queue composes existing manual review state with existing technical tuning attention so operators can triage scopes faster from cockpit:

- `GET /api/runtime-governor/tuning-review-queue/`
- `GET /api/runtime-governor/tuning-review-queue/<source_scope>/`
- list filters: `unresolved_only=true|false` (default `true`), `effective_review_status=<status>`, `limit=<int>` (default `8`)

`/cockpit` now consumes this queue in **Runtime Tuning Review Queue** and keeps deep investigation anchored in `/runtime?tuningScope=<scope>&investigate=1`. This remains paper-only/read-only and does not change runtime tuning operational logic.

### Runtime Tuning Review Queue Aging (Prompt 185)

A new read-only runtime-governor aging layer now complements the existing human review queue:

- `GET /api/runtime-governor/tuning-review-aging/`
- `GET /api/runtime-governor/tuning-review-aging/<source_scope>/`
- list query params: `unresolved_only` (default `true`), `age_bucket` (`FRESH|AGING|OVERDUE`), `limit` (default `8`)

Aging buckets are deterministic and paper-only:
- `FRESH`: `< 2` full days
- `AGING`: `2-6` full days
- `OVERDUE`: `>= 7` full days

Cockpit now adds a compact **Review Aging** subsection above Runtime Tuning Review Queue and shows per-item aging badges (`age_bucket`, `age_days`, overdue hint) while preserving existing manual review actions and runtime handoff (`/runtime?tuningScope=<scope>&investigate=1`). No runtime/tuning operational logic changed.

## Runtime Tuning Autotriage Digest (Prompt 188)

A compact read-only **Runtime Tuning Autotriage Digest** now consolidates existing runtime tuning human-review signals (queue + aging + escalation + recent activity) into one deterministic operator signal.

- `GET /api/runtime-governor/tuning-autotriage/`
- `GET /api/runtime-governor/tuning-autotriage/<source_scope>/`
- query params: `top_n` (default `3`, max `3`) and `include_monitor` (default `false`)

Digest modes are deterministic and explainable:
- `REVIEW_NOW`
- `REVIEW_SOON`
- `MONITOR_ONLY`
- `NO_ACTION`

This reduces manual scanning across multiple tuning review subsections by publishing one next-action signal (`next_recommended_scope`) plus up to 3 top scopes. The layer is read-only, paper-only, and does not change runtime/tuning operational behavior.

## Mission Control Test Console (Backend, V1 paper)

Se agregó un **Test Console** backend-only para diagnóstico operativo de V1 paper en un solo flujo consolidado.

Nuevos endpoints (`/api/mission-control/...`):
- `POST test-console/start/` inicia una prueba orquestada (bootstrap, scan, trial, validation, trend, gate, extended-run opcional).
- `POST test-console/stop/` aplica una detención conservadora y explícita (pausa sesión/heartbeat si existe mecanismo seguro).
- `GET test-console/status/` devuelve estado consolidado compacto del ciclo de prueba.
- `GET test-console/export-log/?format=text|json` exporta resumen copy-paste friendly (`text`) o estructurado (`json`).

Diagnóstico downstream consolidado (scan exitoso pero pipeline frenado):
- El funnel y el Test Console ahora publican `handoff_summary` compacto con:
  - `shortlisted_signals`
  - `handoff_candidates`
  - `consensus_reviews`
  - `prediction_candidates`
  - `risk_decisions`
  - `paper_execution_candidates`
  - `handoff_reason_codes`
- Se añade `shortlist_handoff_summary` para aislar el primer corte real `shortlist -> handoff`:
  - `shortlisted_signals`, `handoff_attempted`, `handoff_created`, `handoff_blocked`
  - `shortlist_handoff_reason_codes` (compactos) y hasta 3 ejemplos (`signal_id`/`market_id` + `reason_code`)
  - permite distinguir explícitamente: shortlist sin intento, intento bloqueado, promoción creada
- Se añade `consensus_alignment` para evitar diagnóstico engañoso:
  - `consensus_reviews`
  - `shortlist_aligned_consensus_reviews`
  - `consensus_aligned_with_shortlist` (si `false`, consensus reciente está desacoplado del shortlist actual)
- El funnel agrega explainability para `STALLED/BLOCKED` con:
  - `stalled_reason_code`
  - `stalled_missing_counter` (incluye puntero real para `risk` vía `risk_decision_count`)
  - `stage_source_mismatch` (mismatch entre entidades producidas/leídas downstream)
  - `funnel_summary` enriquecido con contexto de handoff
- Se añade `prediction_intake_summary` para diagnosticar explícitamente el tramo `handoff -> prediction`:
  - `handoff_candidates`, `prediction_intake_attempted`, `prediction_intake_created`, `prediction_intake_blocked`
  - `prediction_intake_missing_fields`, `prediction_intake_guardrail_blocked`
  - `prediction_intake_reason_codes` + `prediction_intake_examples` (máx 3: `handoff_id`, `market_id`, `expected_route`, `reason_code`, `missing_fields`)
  - distingue “handoff creado pero intake no intentado” vs “intentado y bloqueado por guardrail/filtro/campos”.
- Bridge conservador: cuando hay handoff elegible y no existe intake reciente, se intenta `prediction_intake_review` con dedupe natural por candidato existente, sin bypass de guardrails posteriores.
- **Prompt 231** repara el bridge real `handoff -> prediction_intake_review` para que no etiquete como `PREDICTION_INTAKE_ROUTE_MISSING` cuando la ruta sí está disponible:
  - diferencia explícitamente `PREDICTION_INTAKE_ROUTE_AVAILABLE`, `PREDICTION_INTAKE_ATTEMPTED`, `PREDICTION_INTAKE_CREATED`, `PREDICTION_INTAKE_REUSED_EXISTING_CANDIDATE` y bloqueos reales (`..._BLOCKED_BY_FILTER`, `..._BLOCKED_BY_GUARDRAIL`, `..._NO_ELIGIBLE_HANDLER`).
  - evita falsos “route missing” por falta de intake run reciente cuando el handler existe.
  - mantiene enfoque observability-first y postura **REAL_READ_ONLY + PAPER_ONLY** (sin live trading real).
- **Prompt 233** agrega diagnóstico explícito de guardrails/filtros de prediction intake:
  - `prediction_intake_guardrail_reason_codes`, `prediction_intake_filter_reason_codes`, `prediction_intake_guardrail_summary`.
  - separación semántica entre guardrail real (`mission_control_precheck`) vs filtro de elegibilidad/reuse/dedupe.
  - `prediction_intake_eligible_count`, `prediction_intake_ineligible_count`, `prediction_intake_reused_count` para distinguir creación útil vs reuse vs bloqueo.
  - `prediction_intake_examples` ahora incluye `handoff_status`, `handoff_confidence`, `guardrail_name`/`filter_name`, `observed_value`, `threshold`, `blocking_stage`.
  - mantiene postura **observability-first + REAL_READ_ONLY + PAPER_ONLY**; no relaja safety/risk de forma indiscriminada.
- **Prompt 235** agrega diagnóstico explícito del handoff scoring/status antes de prediction:
  - `handoff_scoring_summary` con `handoff_ready`, `handoff_deferred`, `handoff_blocked`, `handoff_status_reason_codes`, `ready_threshold`, `deferred_reasons`.
  - `handoff_scoring_examples` (máx 3) con `status_reason_code`, `source_stage`, `observed_value`, `threshold` y `scoring_components`.
  - reason codes operacionales para distinguir `HANDOFF_STATUS_DEFERRED_LOW_CONFIDENCE`, `...NO_PROMOTION`, `...INSUFFICIENT_EVIDENCE`, `...READY_BY_CONSENSUS`, `...READY_BY_PURSUIT`.
  - coherencia semántica en export de prediction intake: guardrail/filtro se reportan en listas separadas, sin mezclar `FILTER_REJECTED` cuando `filter_reason_codes=none`.
  - se mantiene enfoque observability-first y límites **REAL_READ_ONLY + PAPER_ONLY** sin habilitar live trading.
- **Prompt 237** agrega promoción conservadora para handoffs borderline en V1 paper local/test:
  - no baja el `ready_threshold` global (`0.5500`) para el flujo normal `READY`.
  - habilita una vía auditada solo para `DEFERRED` en banda `[0.4500,0.5500)` que cumplen criterios estrictos (market link válido, campos completos, narrativa/divergencia mínimas, sin bypass policy/risk/safety).
  - el bridge habilita solo `prediction_intake` (no paper execution directa) y mantiene **REAL_READ_ONLY + PAPER_ONLY**.
  - añade `handoff_borderline_summary` + `handoff_borderline_examples` (máx 3) para mostrar elegibles/promovidos/bloqueados y reason codes explícitos.
  - el export reporta explícitamente cuándo prediction intake fue habilitado por la regla borderline conservadora.
- **Prompt 239** agrega diagnóstico explícito de `structural weakness` y override conservador (solo V1 paper local/test):
  - nuevo `handoff_structural_summary` + `handoff_structural_examples` (máx 3) con `structural_pass/block`, componentes débiles/fuertes, valores observados, reglas/thresholds y reason codes (`HANDOFF_STRUCTURAL_WEAK_ACTIVITY`, `..._TIME_WINDOW`, `..._ACTIVITY_AND_TIME_WINDOW`, `..._OVERRIDE_BORDERLINE`, etc.).
  - cuando el bloqueo borderline es estructural, el export deja trazabilidad accionable (qué componente bloqueó, valor observado, mínimo esperado y si fue regla individual vs agregada), evitando el genérico único.
  - ajuste conservador: permite override estructural solo si la debilidad activity/time-window no es extrema y existe combinación fuerte de volumen+liquidez+narrativa+divergencia; mantiene guardrails posteriores intactos.
  - sigue siendo observability-first, **REAL_READ_ONLY + PAPER_ONLY**, sin habilitar live trading real.
- **Prompt 241** alinea `prediction intake -> funnel visibility -> risk route` para eliminar falsos `prediction_candidates=0`:
  - añade `prediction_visibility_summary` + `prediction_visibility_examples` (máx 3) con separación explícita `created` vs `reused` vs `visible_in_funnel`.
  - `prediction_candidates` en `handoff_summary` ahora refleja candidatos de intake visibles downstream (no solo conviction reviews en ventana).
  - reason codes explícitos de visibilidad/ruta (`PREDICTION_VISIBLE_IN_FUNNEL`, `PREDICTION_REUSED_BUT_NOT_COUNTED`, `PREDICTION_HIDDEN_BY_STATUS_FILTER`, `PREDICTION_READY_FOR_RISK`, `PREDICTION_NOT_READY_FOR_RISK`, `PREDICTION_RISK_ROUTE_MISSING`).
  - añade `prediction_risk_summary` compacto (`risk_route_expected`, `risk_route_available`, `risk_route_attempted`, `risk_route_reason_codes`) para exponer el siguiente cuello real sin bypass de risk.
  - mantiene enfoque observability-first y fronteras **REAL_READ_ONLY + PAPER_ONLY**; sin live trading real.
- **Prompt 243** amplía diagnóstico y bridge conservador `prediction -> risk` en Mission Control:
  - `prediction_risk_summary` ahora reporta `risk_route_expected`, `risk_route_available`, `risk_route_attempted`, `risk_route_created`, `risk_route_blocked`, `risk_route_missing_status_count`, `risk_route_reason_codes`, `risk_route_summary`.
  - agrega `prediction_risk_examples` (máx 3) con `candidate_id`, `market_id`, `source_model`, `prediction_status`, `expected_route`, `reason_code`, `blocking_stage`, `observed_value`, `threshold`.
  - distingue explícitamente la verdad operacional entre:
    - candidate visible pero sin artefacto esperado por risk (`PredictionIntakeCandidate` sin `PredictionConvictionReview` listo),
    - filtro de status (`MONITOR_ONLY` o review no `READY_FOR_RISK`),
    - handler/route no disponible,
    - bridge intentado, decisión creada, o decisión reutilizada.
  - incorpora bridge mínimo a `run_risk_runtime_review` **solo** cuando hay candidate visible + elegible + sin decisión previa, manteniendo dedupe, policy/safety y modo **REAL_READ_ONLY + PAPER_ONLY** (sin live trading real).
- **Prompt 245** agrega diagnóstico explícito de `prediction_status` y ajuste conservador `MONITOR_ONLY -> READY_FOR_RUNTIME`:
  - nuevo `prediction_status_summary` + `prediction_status_examples` (máx 3) con conteos (`monitor_only`, `ready_for_runtime`, `blocked`), reason codes y umbral operativo para runtime-ready.
  - cada ejemplo expone trazabilidad accionable (`status_reason_code`, `observed_value`, `threshold`, `source_stage`, confidence/edge/uncertainty y lineage resumido) para distinguir bloqueo correcto vs regla demasiado conservadora.
  - ajuste conservador de intake para V1 local/test: habilita `READY_FOR_RUNTIME` con `PREDICTION_STATUS_READY_WITH_CAUTION` cuando la confianza es borderline pero la lineage (narrative + pursuit) es fuerte; no bypass de risk/policy/safety.
  - si el candidate es `reused` y conserva `MONITOR_ONLY`, el diagnóstico lo marca explícitamente (`PREDICTION_STATUS_MONITOR_ONLY_REUSED_STATUS`) sin promoción masiva.
  - mantiene observability-first y fronteras **REAL_READ_ONLY + PAPER_ONLY**, sin live trading real.
- **Prompt 247** agrega una vía auditada `MONITOR_ONLY -> risk runtime review with caution` (sin bajar el threshold global):
  - mantiene `runtime_ready_threshold=0.5500` como regla base de `READY_FOR_RUNTIME`; no promueve masivamente `MONITOR_ONLY`.
  - introduce `prediction_risk_caution_summary` + `prediction_risk_caution_examples` (máx 3) para mostrar candidatos monitor-only evaluados en banda conservadora (`[0.4500,0.5500)`) con edge/lineage/policy checks explícitos.
  - agrega reason codes accionables (`PREDICTION_RISK_WITH_CAUTION_ELIGIBLE`, `..._PROMOTED`, `..._BLOCKED_BY_LOW_EDGE`, `..._BLOCKED_BY_WEAK_LINEAGE`, `..._BLOCKED_BY_POLICY_SIGNAL`, `..._NOT_IN_BAND`, `..._REUSED`).
  - Mission Control permite llegar únicamente a `risk_runtime_review` cuando el candidate `MONITOR_ONLY` cumple la regla de cautela y ya está `READY_FOR_RISK` en conviction review; no habilita paper execution directa ni relaja risk/policy/safety.
  - mantiene límites estrictos **REAL_READ_ONLY + PAPER_ONLY** y sin live trading real.
- **Prompt 249** corrige mismatch de artefactos `PredictionIntakeCandidate -> PredictionConvictionReview -> RiskReadyPredictionHandoff` en el bridge prediction->risk:
  - agrega `prediction_artifact_summary` + `prediction_artifact_examples` (máx 3) para diagnóstico explícito de expected/available/created/reused/bloqueado por artefacto.
  - Mission Control materializa/reutiliza de forma conservadora `PredictionConvictionReview` y `RiskReadyPredictionHandoff` para candidatos visibles (sin bypass de risk/policy/safety y con dedupe natural).
  - reason codes trazables: `PREDICTION_CONVICTION_REVIEW_{MISSING|CREATED|REUSED}`, `PREDICTION_RISK_READY_HANDOFF_{MISSING|CREATED|REUSED}`, `PREDICTION_ARTIFACT_MISMATCH_{RESOLVED|BLOCKED}`.
  - export log ahora deja explícito si faltaba conviction review, si se creó/reusó conviction review/handoff y si `prediction_risk_summary` avanzó por resolver el mismatch.
  - mantiene alcance observability-first, **REAL_READ_ONLY + PAPER_ONLY**, sin frontend, sin `/runtime`, sin paper execution directa ni live trading real.
- **Prompt 253** agrega diagnóstico explícito del tramo `risk -> paper_execution` (sin reparar todavía el bridge):
  - añade `paper_execution_summary` con métricas compactas: `route_expected`, `route_available`, `route_attempted`, `route_created`, `route_reused`, `route_blocked`, `route_missing_status_count`, `paper_execution_route_reason_codes`.
  - añade `paper_execution_examples` (máx 3) con `risk_decision_id`, `market_id`, `decision_status`, `expected_route`, `reason_code`, `blocking_stage`, `observed_value`, `threshold`.
  - separa explícitamente la verdad operacional entre:
    - risk decision no enrutable por status (`PAPER_EXECUTION_STATUS_FILTER_REJECTED`),
    - route/handler faltante (`PAPER_EXECUTION_ROUTE_MISSING`, `PAPER_EXECUTION_NO_ELIGIBLE_HANDLER`),
    - bloqueo por policy/safety/runtime,
    - reuse/creación de candidate de execution (`PAPER_EXECUTION_REUSED_EXISTING_CANDIDATE`, `PAPER_EXECUTION_CREATED`),
    - mismatch de artefacto (`PAPER_EXECUTION_ARTIFACT_MISMATCH`).
  - integra el diagnóstico en el funnel snapshot y en el export del Test Console (`text/json`) sin logging paralelo.
  - mantiene scope observability-first + **REAL_READ_ONLY + PAPER_ONLY**, sin frontend, sin `/runtime`, sin live trading real.
- **Prompt 255** alinea visibilidad/counting de `paper_execution_candidates` entre funnel y Test Console:
  - `handoff_summary.paper_execution_candidates` ahora refleja visibilidad operacional de candidates de `execution_intake` (no ejecuciones/fills finales), evitando falsos `0` cuando `paper_execution_summary` ya reportaba `route_created/route_reused`.
  - nuevo `paper_execution_visibility_summary` + `paper_execution_visibility_examples` (máx 3) con conteos `created/reused/visible/hidden`, reason codes y trazabilidad por `risk_decision_id`/`execution_candidate_id`.
  - reason codes compactos para distinguir: visible real, hidden por ventana/status, created/reused no contados y mismatch de source model (`AutonomousExecutionReadiness` vs `AutonomousExecutionIntakeCandidate`).
  - el export log del Test Console agrega bloque explícito de visibilidad para explicar el caso “route OK pero `paper_execution_candidates=0`”.
- **Prompt 257** cierra el tramo final `AutonomousExecutionReadiness -> candidate visible` sin abrir ejecución monetaria:
  - agrega `execution_artifact_summary` + `execution_artifact_examples` (máx 3) para distinguir readiness creado/reusado, candidate visible creado/reusado, hidden y bloqueos reales de artifact mismatch.
  - cuando existe readiness elegible pero falta `AutonomousExecutionIntakeCandidate`, Mission Control materializa de forma conservadora un candidate paper-only (`dispatch_enabled=false`) para resolver el mismatch de modelo sin forzar fills/trades.
  - `handoff_summary.paper_execution_candidates` queda alineado con `execution_candidate_visible_count` downstream, manteniendo observability-first, `REAL_READ_ONLY` y `PAPER_ONLY`.
  - sigue observability-first, backend-only y **REAL_READ_ONLY + PAPER_ONLY**; no abre candidate->fill ni live trading real.
- **Prompt 259** agrega diagnóstico explícito del último tramo `execution candidate visible -> paper trade/trade cycle`:
  - nuevo `paper_trade_summary` con `paper_trade_route_expected|available|attempted|created|reused|blocked` y `paper_trade_route_reason_codes`.
  - `paper_trade_examples` (máx 3) muestra `execution_candidate_id`, `market_id`, `candidate_status`, `expected_route`, `reason_code`, `blocking_stage`, `observed_value`, `threshold`.
  - separa visibilidad de candidate vs ejecutabilidad real (`READY_FOR_AUTONOMOUS_EXECUTION|READY_REDUCED`) y deja explícitos bloqueos por status, runtime, policy/safety, dedupe/reuse y artifact mismatch.
  - añade `execution_lineage_summary` para distinguir reuse histórico/fan-out legítimo vs fan-out excesivo (`fanout_reason_codes`).
  - el export del Test Console incluye ambos bloques (`paper_trade_summary`, `execution_lineage_summary`) en texto y JSON, manteniendo enfoque observability-first y **REAL_READ_ONLY + PAPER_ONLY**.
- **Prompt 261** repara el bridge final `AutonomousExecutionIntakeCandidate -> AutonomousExecutionDecision` en paper-only con contención conservadora de fan-out:
  - Mission Control crea o reutiliza `AutonomousExecutionDecision` para candidates ejecutables visibles, sin abrir live trading ni broker routing.
  - añade dedupe final por lineage/market (market + ancestry de readiness/approval/sizing/watch/prediction context) para evitar decisiones equivalentes duplicadas.
  - nuevo bloque `paper_trade_decision_summary` + `paper_trade_decision_examples` en Test Console export (`text/json`) con `decision_created|reused|blocked|dedupe_applied` y reason codes explícitos.
  - `execution_lineage_summary` ahora expone `candidates_considered`, `candidates_deduplicated`, `decisions_created` y `decisions_reused` para distinguir fan-out legítimo vs dedupe aplicada.
  - mantiene enfoque observability-first, backend-only y límites **REAL_READ_ONLY + PAPER_ONLY**; no mezcla todavía fill/settlement ni rediseña `/runtime`.
- **Prompt 263** repara el bridge final `AutonomousExecutionDecision -> AutonomousDispatchRecord` sin abrir live trading real:
  - Mission Control ahora crea o reutiliza `AutonomousDispatchRecord` en paper-only para decisiones ejecutables visibles cuando faltaba `dispatch_record` (`missing_dispatch_record`), con dedupe conservadora por lineage/market.
  - agrega `paper_trade_dispatch_summary` + `paper_trade_dispatch_examples` en export log (`text/json`) con `dispatch_created|dispatch_reused|dispatch_blocked|dispatch_dedupe_applied` y reason codes explícitos.
  - alinea la verdad operacional entre `paper_trade_decision_summary` y `execution_lineage_summary` (`decisions_created|decisions_reused`) para evitar contradicciones diagnósticas.
  - refuerza reason codes de fan-out/dedupe final (`LINEAGE_FANOUT_EXPECTED`, `LINEAGE_DEDUPE_REUSED_EXISTING_DISPATCH`) manteniendo enfoque observability-first.
  - mantiene límites **REAL_READ_ONLY + PAPER_ONLY**: backend-only, sin frontend, sin tocar `/runtime`, sin broker real ni dinero real.
- **Prompt 265** repara el último bridge `AutonomousDispatchRecord -> linked_paper_trade_id` en paper-only:
  - Mission Control materializa/reutiliza el trade final cuando existe dispatch `QUEUED|DISPATCHED|PARTIAL|FILLED` sin `linked_paper_trade_id`, enlazando también `AutonomousTradeExecution` y `AutonomousTradeCycleRun` cuando aplica.
  - agrega dedupe conservadora final por lineage/market para evitar multiplicar trades prácticos del mismo caso (`LINEAGE_DEDUPE_REUSED_EXISTING_TRADE`, `LINEAGE_DEDUPE_BLOCKED_DUPLICATE`).
  - añade `paper_trade_final_summary` + `paper_trade_final_examples` en export (`text/json`) con `expected|available|attempted|created|reused|blocked` y `final_trade_reason_codes`.
  - enriquece `execution_lineage_summary` con `dispatches_considered`, `dispatches_deduplicated`, `trades_materialized`, `trades_reused` para hacer explícita la contención del fan-out final.
  - mantiene frontera **REAL_READ_ONLY + PAPER_ONLY**, sin live trading real, sin frontend y sin rediseño de `/runtime`.
- **Prompt 266** corrige el desacople entre funnel/gate y portfolio real en Mission Control:
  - agrega diagnóstico reusable `state_mismatch_summary` + `state_mismatch_examples` (máx 3) en Test Console export para explicar inconsistencias entre control plane y estado operacional real.
  - reason codes explícitos de consistencia (`STATE_SESSION_MISMATCH`, `STATE_WINDOW_MISMATCH`, `STATE_SCOPE_MISMATCH`, `STATE_EMPTY_FALLBACK_APPLIED`, `STATE_PORTFOLIO_ACTIVE_BUT_FUNNEL_EMPTY`, `STATE_GATE_BLOCKED_ON_STALE_VIEW`, `STATE_ALIGNMENT_OK`).
  - `extended_paper_run_gate` ahora expone fuentes operacionales de cálculo (`gate_source_summary`) y evita bloquear solo por funnel `STALLED` cuando detecta vista stale (portfolio activo + funnel vacío por ventana), sin relajar validación/readiness/attention.
  - mantiene enfoque observability-first y límites estrictos **REAL_READ_ONLY + PAPER_ONLY** (sin frontend, sin `/runtime`, sin live trading real).
- Esta consolidación ya integra el fix posterior de funnel:
  - `SHORTLIST_PRESENT_NO_HANDOFF` sólo si hay shortlist real + ausencia de handoff.
  - No depende sólo de `stalled_stage == "research"`.
- **Prompt 267** estabiliza el tramo final paper-only sin tocar `/runtime` ni live trading real:
  - agrega `final_fanout_summary` + `final_fanout_examples` (máx 3) para diagnosticar fan-out final por lineage/market con `duplicate_execution_candidates|duplicate_dispatches|duplicate_trades`, `final_fanout_status` y reason codes (`FINAL_LINEAGE_*`).
  - mantiene contención conservadora en el puente final (dedupe/reuse de trade válido existente por lineage/market) para evitar multiplicación artificial sin borrar historial ni alterar fills ya materializados.
  - agrega `portfolio_trade_reconciliation_summary` para reconciliar explícitamente `materialized_paper_trades`, `reused_trade_cycles`, `recent_trades_count`, `open_positions`, `equity` y `unrealized_pnl` con reason codes (`PORTFOLIO_*`).
  - el export log del Test Console (`text/json`) incorpora ambos bloques compactos (`final_fanout_summary`, `portfolio_trade_reconciliation_summary`) sin logging paralelo.
  - agrega `active_operational_overlay_summary` para diagnosticar cuándo la rolling window está vacía pero el sistema sigue operativamente activo por portfolio/trades fuera de ventana.
  - diferencia explícitamente `funnel_status_window` (actividad real de la ventana) vs `funnel_status` efectivo (`ACTIVE_WITHOUT_RECENT_FLOW` cuando aplica carry-forward), sin inventar handoff/prediction/risk/exec recientes.
  - mantiene enfoque observability-first con `REAL_READ_ONLY + PAPER_ONLY` (sin habilitar live trading real).
  - mantiene enfoque observability-first y límites **REAL_READ_ONLY + PAPER_ONLY**.

Boundary de seguridad:
- Mantiene postura **REAL_READ_ONLY + PAPER_ONLY**.
- No habilita live trading real.
- No crea scheduler nuevo ni arquitectura pesada de auditoría.


### Mission Control LLM smoke test corto (Prompt 306)

Para iterar rápido sobre integración LLM local (Ollama + normalización shadow + persistencia + aux signal) sin correr la prueba larga de 40–60+ minutos, ahora existe un comando corto:

- `python apps/backend/manage.py run_llm_shadow_smoke`

Opciones útiles:
- `--model <modelo>`: override de modelo solo para esta ejecución.
- `--timeout <segundos>`: override de timeout solo para esta ejecución.
- `--aux-signal` / `--no-aux-signal`: forzar toggle local de `OLLAMA_AUX_SIGNAL_ENABLED`.
- `--json`: salida compacta en JSON para inspección rápida/scriptable.

Qué valida:
- llamada real a Ollama (si está disponible),
- construcción y normalización de `llm_shadow_summary`,
- persistencia de artefacto (`artifact_id` cuando aplica),
- cálculo de `llm_aux_signal_summary`,
- límites de seguridad (`advisory_only=true`, `affects_execution=false`, `paper_only=true`).

Qué **no** valida:
- shortlist/handoff/prediction/risk/execution end-to-end,
- ni reemplaza la prueba completa de Mission Control; es un smoke test de capa LLM.

### Prompt 321 — scope/window/lineage alignment (backend-only)

- Se corrigió el fanout operativo de Mission Control para que `risk_decisions` y rutas de execution cuenten solo artefactos elegibles del **current window + current lineage**.
- **No hay cambios de policy**.
- **No se elimina historial de auditoría**: los artefactos históricos/out-of-scope siguen visibles en diagnóstico, pero dejan de inflar fanout operativo actual.

## Test Console backend-only test profiles

`apps/backend` now supports backend-only Test Console profiles to run targeted diagnostics faster without policy or trading-logic changes. Use `profile_id` on `POST /api/mission-control/test-console/start/`; default remains `full_e2e`.

Export/status include `test_profile`, `modules_included`, `modules_omitted`, and `run_scope` (`fresh_full_run` vs `targeted_diagnostic_run`).

- Frontend hardening: fixed avoidable 404 wiring in Dashboard/Markets/Portfolio and converted optional missing resources to clean empty-state handling (no fatal UX break).

### Stabilization audit note (2026-04-22)

Se registró una auditoría técnica estructural (sin refactor masivo ni cambios de policy) con foco en Mission Control, Test Console, Cockpit/Advanced y lifecycle `status/export/snapshot`.

Documento:
- `docs/architecture/stabilization-audit-2026-04-22.md`

Incluye:
- Top 10 hotspots técnicos con severidad/síntoma/módulos/recomendación.
- Priorización de quick wins vs fixes medianos vs refactors grandes.
- Plan de estabilización en 3 fases: (1) lifecycle/contracts, (2) polling/state/UI sync, (3) consolidación/cleanup.
