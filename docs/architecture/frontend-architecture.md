# Frontend architecture

## Purpose

The frontend is a local-first operator workspace for `market-trading-bot`.

In the current phase it focuses on these responsibilities:

1. provide a professional application shell
2. expose clear navigation for the existing demo modules
3. surface technical backend health and local runtime context
4. present a useful dashboard powered by real local demo data
5. connect discovery, signals, proposals, risk, policy, paper execution, portfolio, and post-mortem into one coherent demo flow
6. keep the architecture intentionally simple: no websockets, no global state framework, no realtime orchestration, no new heavy routing model
7. support read-only exploration of real provider markets without blurring the boundary with demo/paper execution
8. include explicit post-entry position lifecycle governance via `/positions` (hold/reduce/close/review with paper-only execution paths)

## Current UX narrative

The frontend now tries to tell one clear story:

1. discover an opportunity
2. inspect the market
3. review the demo signal
4. generate and inspect a trade proposal
5. evaluate the trade with the risk guard
6. evaluate the operational approval decision with the policy engine
7. execute a paper trade only when the policy result allows it
8. inspect portfolio impact
9. review the post-mortem

This is accomplished mostly with **navigation refinements, cross-module summaries, empty-state guidance, and lightweight refresh coordination**, not with a new architecture.

## Structure

The frontend source tree remains intentionally shallow and practical:

- `app/`: app composition and shared providers
- `components/`: reusable presentation building blocks, including dedicated dashboard, markets, paper trading, signals, postmortem, and flow UI
- `hooks/`: page-agnostic frontend behavior
- `layouts/`: app shell and persistent navigation structure
- `lib/`: static config and lightweight helpers
- `pages/`: route-level views
- `services/`: API requests and backend integration points
- `styles/`: global styling
- `types/`: shared UI and API types
- `store/`: reserved for future shared state if it becomes necessary

## Routing approach

The frontend still uses a lightweight in-app browser-history router.

That remains a deliberate choice because this stage required better **continuity** between routes, not a routing rewrite.

The current router is enough for:

- persistent shell layout
- sidebar navigation
- browser back/forward support
- route-specific context
- linked review detail routes
- contextual navigation between modules

## Data integration strategy

The frontend still avoids a heavy client-state layer.

Instead, each page coordinates a small set of explicit service calls.

### Service boundaries

- `services/markets.ts` for catalog and detail views
- `services/signals.ts` for legacy signals + fusion runs + opportunity board + proposal-gate actions
- `services/proposals.ts` for trade proposal list, detail, and generation endpoints
- `services/paperTrading.ts` for account, positions, trades, snapshots, summary, and revalue
- `services/positions.ts` for lifecycle runs, lifecycle decisions, summary cards, and run triggers
- `services/reviews.ts` for review summary, list, and detail
- `services/riskDemo.ts` for pre-trade assessment
- `services/policy.ts` for trade approval evaluation and policy decision summaries
- `services/experiments.ts` for strategy profiles, experiment runs, and run comparisons
- `services/research.ts` for mixed narrative source management (`RSS` + `REDDIT` + optional `TWITTER`), ingest/analysis/full-scan controls, and shortlist/candidate data.
- `services/policyRollout.ts` for rollout-monitor start/list/detail/evaluate/rollback/summary APIs tied to post-change policy tuning governance.

This keeps data dependencies understandable and prevents the current demo phase from turning into a client-state rewrite.

### Precedent-aware data surfaces (new)

- `services/memory.ts` now includes precedent-use and influence-summary audit calls.
- Existing pages consume precedent context from existing payload metadata/details instead of adding heavyweight new routes.
- UX pattern:
  - show concise badges (`PRECEDENT_AWARE`, caution/history labels)
  - show explicit empty valid result (`No strong precedents found for this case.`)
  - keep manual operator control and avoid autonomous opaque behavior

## Lightweight cross-page refresh strategy

One of the most important refinements in this phase was improving consistency after actions.

The chosen approach is intentionally small:

- key pages reload their local data on focus / visibility regain
- the frontend publishes a lightweight custom refresh event after:
  - paper trade execution
  - portfolio revalue
- Dashboard, Signals, Portfolio, Post-mortem, and Market detail listen for that event and refetch their own page-local context

Why this approach:

- avoids introducing websocket or polling infrastructure
- avoids adding a global state library too early
- keeps page ownership explicit
- improves consistency after meaningful workflow actions
- matches the local-first, demo-only scope

## Cross-module UX components added in this phase

A few small reusable UI primitives now help the app feel integrated without overengineering:

- `WorkflowStatusPanel`
- `ContextLinksPanel`
- refined workflow-aware table links in Signals, Portfolio, and Post-mortem

These components do not introduce a new design system. They reuse existing page patterns and only add enough structure to make the narrative visible.

## Route responsibilities

### Dashboard

The home route now acts as a true entry point for the demo flow:

- quick links aligned to the real workflow
- current demo flow summary
- small cross-module indicators for markets, signals, positions, and reviews
- lightweight recent markets and recent signals context

### Signals

The `/signals` route remains intentionally simple, but now works as a bridge instead of a dead-end table:

- signal rows link into market detail
- workflow context can expose related positions and reviews
- page-level context blocks explain when to continue into Markets, Portfolio, or Post-mortem

### Proposals

The `/proposals` route provides a desktop-first proposal inbox:

- generated proposal list with thesis and headline context
- direction / suggested quantity / score / confidence
- risk and policy decision visibility with actionable status
- links into market detail to continue toward manual execution

### Market detail

The `/markets/:marketId` route is now the operational hub of the demo:

- market context
- recent signals
- proposal generation and proposal bridge panel
- risk assessment
- policy approval decision
- paper trade execution
- position / latest trade / latest review summary
- direct next-step links into Portfolio and Post-mortem
- explicit source context:
  - source badge (`DEMO` vs `REAL · READ-ONLY`)
  - provider badge
  - read-only warning when the market comes from a real provider source
  - explicit reminder that trading in the app still remains paper/demo only
  - explicit `execution_mode`, `paper_tradable`, and `paper_tradable_reason` context in overview and trade panel
  - blocked CTA behavior when a market is not paper-tradable

### Portfolio

The `/portfolio` route is now more clearly positioned as the impact view:

- positions link back to market detail
- trade rows link to reviews when available
- review summary block surfaces recent retrospective context
- empty states suggest the next useful step instead of only showing missing data
- position and trade rows now surface market source + execution mode to avoid confusion between real read-only pricing and simulated execution

### Post-mortem

The `/postmortem` route now closes the loop more clearly:

- review queue with explicit workflow links
- detail view with clearer trade, signal, and risk context
- contextual links back to Market detail and Portfolio

### Policy rollout

The `/policy-rollout` route is the post-change monitoring board for applied policy tuning changes:

- start rollout monitors from applied candidates
- show active rollout status and recommendation outcome
- compare baseline vs post-change metrics + deltas in one technical panel
- expose manual rollback control with approval/trace-oriented navigation
- keep empty/loading/error states explicit and audit-friendly

### Autonomy advisory

The new `/autonomy-advisory` route adds a dedicated insight-action emission board without redesigning the shell:

- integrates `services/autonomyAdvisory.ts` for candidates, run-review, artifacts, recommendations, summary, and manual emit actions
- renders manual-first summary cards + candidate routing table + artifact history + recommendation queue
- keeps states explicit (`READY`, `BLOCKED`, `EMITTED`, `DUPLICATE_SKIPPED`, `ACKNOWLEDGED`)
- links into `/autonomy-insights`, `/cockpit`, and `/trace` for drill-down continuity

Design intent remains conservative: no auto-apply, no opaque automation, and no real-execution behaviors.

### Research

The `/research` route acts as the scan/research operator console:

- source panel differentiating RSS, Reddit, and X/Twitter sources
- run controls for ingest-only, analysis-only, and full research scan
- narrative item table with source-type badges and sentiment/confidence signals
- shortlist table with mixed-source metadata (`source_mix`, divergence, priority)

Current non-goals remain explicit: no aggressive social scraping/crawling, no real execution.

## UI principles for this stage

- sober, readable visual design
- incremental evolution over redesign
- section-level failure isolation
- contextual navigation instead of long onboarding
- better empty states instead of cold "no data" messages
- consistent labels for actionability, risk decision, trade status, and review outcome
- explicit source distinction (demo vs real read-only) in list and detail views
- explicit paper tradability distinction for real read-only markets (tradable vs blocked with reason)
- no unnecessary client complexity

## Explicitly not introduced yet

This phase intentionally does **not** introduce:

- realtime updates
- websocket architecture
- advanced global client state
- interactive tutorial flows
- redesign of routing boundaries
- real provider integrations
- real signals / ML / autonomous trading
- complex orchestration infrastructure

## Planned evolution

The next reasonable frontend steps can still build on this architecture:

## Execution realism UI integration (new)

Execution realism is integrated by extending existing views instead of creating a new frontend subsystem:

- `/replay` adds execution mode/profile controls and execution-aware result cards.
- `/evaluation` surfaces execution-adjusted snapshot metrics from backend metadata.
- `/experiments` compares naive and execution-aware runs, including execution drag context.
- `/readiness` shows execution realism impact and readiness penalty context.

This keeps UI coupling low:
- existing services/types (`replay`, `evaluation`, `experiments`, `readiness`) were extended
- no centralized state rewrite
- no new routing architecture

- richer review context if backend heuristics expand
- more nuanced market-to-portfolio linking if execution history becomes denser
- optional refresh controls or lightweight polling only if manual/focus refresh becomes insufficient
- deeper system diagnostics without changing the current app shell

## Automation control center

The frontend now includes an `/automation` route backed by `services/automation.ts` and `types/automation.ts`. This page acts as a guided demo control center: it calls the backend automation endpoints through the shared API client, shows loading and error states, renders recent automation runs, and surfaces step-level results for the full demo cycle. The UX is intentionally explicit and operator-driven so the broader end-to-end workflow can move faster without becoming an autonomous system.

## Prediction governance UX extension

The `/prediction` route now includes a dedicated governance section:

- active model status card
- model comparison controls (baseline/candidate/profile/scope)
- side-by-side comparison history with winner/recommendation badges
- explicit no-auto-switch messaging

Data sources are intentionally thin service calls (`services/prediction.ts`) to:
- `/api/prediction/model-profiles/`
- `/api/prediction/compare-models/`
- `/api/prediction/comparisons/`
- `/api/prediction/active-model-recommendation/`
- `/api/prediction/model-governance-summary/`

## Policy approval UX boundary

The market detail route now makes an explicit distinction between analysis and governance:

- `TradeRiskPanel` explains the analytical trade guard result.
- `PolicyDecisionPanel` explains the operational approval result.

That distinction is important because the product goal has shifted from a set of disconnected demo modules toward a semi-structured decision platform.

Current UX behavior:
- `AUTO_APPROVE` -> execute button is enabled directly after policy evaluation
- `APPROVAL_REQUIRED` -> the panel shows a stronger manual-approval notice and the CTA changes to an explicit confirmation action
- `HARD_BLOCK` -> the CTA stays disabled and the panel suggests concrete fixes

The `/automation` page also reinforces that automation remains operator-driven and that future automated proposals should still pass through the policy layer before any execution step.

- Semi-Auto page (`/semi-auto`) provides evaluate/run controls, safety guardrail overview, pending approval queue, and recent run audit list.


### Safety route and cross-module integration

Frontend includes a dedicated `/safety` route and `services/safety.ts` client bindings. Continuous Demo and Semi-Auto pages consume safety status to explain restrictions and disable unsafe auto actions when cooldown/hard-stop/kill-switch is active.

## Learning route (`/learning`)

Nueva vista técnica para memoria operativa demo:
- consume `/api/learning/summary`, `/api/learning/memory`, `/api/learning/adjustments`
- incluye rebuild controlado vía `/api/learning/rebuild`
- muestra estado loading/error/empty
- enlaza con evaluación y postmortem para cerrar loop de aprendizaje operativo


## Controlled learning loop UX integration

Frontend integration reuses existing route boundaries and service modules:

- `services/learning.ts` now includes rebuild-run and integration-status fetchers.
- `/automation` surfaces explicit controlled-learning actions.
- `/continuous-demo` surfaces whether automatic rebuild is enabled and cadence.
- `/learning` surfaces rebuild-run history plus influence context.

UI strategy remains technical and minimal: cards/tables/badges with explicit loading/error/empty messaging.

## Real sync frontend integration

The frontend now has a dedicated service/type boundary for real-data sync:
- `services/realSync.ts`
- `types/realSync.ts`

Current UX integration points:
- `/system`: provider sync technical panel (status, stale warnings, recent runs, manual trigger)
- `/automation`: explicit `sync_real_data` action in the operator control list

Design intent:
- keep real-data refresh observable and manually controlled
- surface actionable technical state to operators
- avoid introducing autonomous realtime behavior at this stage


### Real Ops frontend slice
The frontend adds a dedicated `/real-ops` route and `realOps` service module.
It focuses on operator visibility and controlled triggers:
- evaluate eligible real-read-only markets
- run autonomous paper-only cycles in the configured scope
- inspect exclusions and sync-aware blocking reasons
- audit recent run outcomes.

This complements (does not replace) `/continuous-demo` and `/automation`.

## Allocation route (`/allocation`)

Nueva ruta frontend orientada a operación técnica:
- consume `services/allocation.ts`
- muestra cards de resumen + tabla de ranking/decisión + historial de runs
- estado loading/error/empty explícito para flujo local-first
- enfatiza que toda ejecución sigue en modo paper/demo

Integración ligera:
- dashboard quick link
- botones desde Real Ops y Continuous Demo hacia `/allocation`

## Operator queue frontend integration

The frontend now includes `/operator-queue` as the centralized exception inbox.

Integration shape:
- service boundary: `src/services/operatorQueue.ts`
- type boundary: `src/types/operatorQueue.ts`
- route/page: `src/pages/operator-queue/OperatorQueuePage.tsx`
- lightweight discoverability links added to dashboard/system quick links and real-ops/continuous pages

UX intent:
- operator only intervenes on exceptions
- clear rationale-first detail view for auditable manual decisions
- simple technical controls (approve/reject/snooze) without enterprise workflow complexity

## Replay UI integration

A dedicated `/replay` route was added with a technical-first layout:
- control panel for historical range and replay config
- latest-run summary cards
- recent-runs technical table
- optional step timeline table

Integration points:
- service module `src/services/replay.ts`
- typed contracts in `src/types/replay.ts`
- cross-link with `/evaluation` for future replay-vs-evaluation comparisons

Scope remains explicit: historical paper/demo simulation only.


## Experiments route integration
The `/experiments` page introduces a technical A/B workflow without changing routing architecture:

- fetches strategy profiles and run history with page-local state
- executes profile-based experiment runs via `/api/experiments/run/`
- compares two runs with `/api/experiments/comparison/`
- links from evaluation/replay to keep navigation continuity

UX remains sober and desktop-first: cards/tables/badges, clear loading/error/empty states, and explicit paper/demo-only messaging.

## Readiness UX layer (new)

The frontend now includes a dedicated `/readiness` route and `services/readiness.ts` bindings.

Responsibilities:
- expose profile-based readiness criteria
- run assessments on demand
- present transparent decision evidence (status, gate counts, failed gates, recommendations)
- keep the operator aware this is governance-only and still paper/demo-only

Integration choices remain lightweight:
- quick links from Evaluation and Experiments to Readiness
- dashboard quick link to readiness module
- no global client-state rewrite

## Runtime governance UX layer (new)

A dedicated `/runtime` route now exposes operational mode governance in the frontend.

UI responsibilities:
- render effective runtime mode and status
- surface readiness/safety influence
- allow explicit operator mode changes when permitted
- explain blocked modes with clear constraints
- display effective capability matrix and transition audit table

Integration is intentionally lightweight:
- route added through existing app router
- API calls isolated in `services/runtime.ts`
- typed contracts in `types/runtime.ts`
- no global state framework changes

This keeps governance auditable and operator-readable while staying local-first and paper/demo only.

## Operator alerts UX layer

A dedicated `/alerts` route now acts as the operator incident center.

### UX structure
- summary cards for immediate attention
- central technical alert table with severity/type/source/status
- detail panel with metadata and suggested operator action
- recent digests table for time-window summaries

### Integration points
- quick links from runtime/safety/system/dashboard pathways
- API integration through `services/alerts.ts` using the shared API client
- explicit empty-state messaging when no critical attention is required

### Out of scope (intentional)
- realtime sockets
- external notification channels
- non-local deployment concerns

## Notifications UI architecture (new)

Se agregó `/notifications` como superficie dedicada para outbound alert delivery:

- consume `services/notifications.ts`
- renderiza configuración (channels/rules) + observabilidad (history/summary)
- expone acciones manuales de envío para alertas y digests
- mantiene lineamientos existentes: vista técnica, sobria, desktop-first

Integraciones ligeras:
- `/alerts` incluye enlace rápido a `/notifications`
- `/alerts` muestra estado de última notificación por alerta
- `/system` muestra bloque de salud de delivery

## Notifications automation UI architecture (new)

The `/notifications` route now acts as the local automation control surface.

Integration split:
- `services/notifications.ts`: automation status/control + dispatch/digest run endpoints + escalation feed
- `types/notifications.ts`: automation and escalation types + trigger-source typing
- `pages/notifications/NotificationsPage.tsx`: cards + control actions + delivery/escalation tables with explicit loading/error/empty states

This keeps automation operator-visible and auditable without introducing realtime sockets or heavy client state.

## Local LLM status visibility

Frontend now includes a minimal integration for local LLM observability:

- `services/llm.ts` calls `GET /api/llm/status/`
- `types/llm.ts` defines status payload typing
- `SystemPage` renders a small status card showing provider/model/reachability

This keeps UX impact intentionally small while exposing whether local Ollama enrichment is available.

## Research UX boundary (`/research`)

The frontend now includes a dedicated `/research` route focused on RSS-first scan/research triage.

Layout strategy:
- summary cards + latest run status
- source configuration visibility
- manual run controls (ingest / analysis)
- recent narrative items table
- shortlist/candidate table with narrative-vs-market relation badges

Integration notes:
- uses `services/research.ts` with the shared API client
- links shortlist rows back to market detail routes
- surfaces degraded-mode messaging when `/api/llm/status/` reports unavailable local LLM

## Prediction route architecture (`/prediction`)

Nueva ruta técnica integrada al shell actual, sin rediseñar routing ni estado global.

### Frontend service boundary

- `services/prediction.ts`
- `types/prediction.ts`

Funciones:
- `getPredictionProfiles`
- `scoreMarketPrediction`
- `getPredictionScores`
- `getPredictionScore`
- `getPredictionSummary`

### UX objetivo

- profiles visibles
- score on-demand por market
- card de resultado con edge/confidence auditable
- tabla de histórico reciente
- estados loading/error/empty explícitos
- degradación clara cuando la capa narrativa basada en LLM no está disponible

## Prediction UI technical panel

`/prediction` now combines runtime scoring and model lifecycle controls:

- runtime summary cards and score flow
- dataset build / train controls
- training runs table
- model registry table with activate action
- explicit fallback messaging when no active trained artifact is available

The UI continues to consume backend APIs as a thin client; training logic remains backend-only.

## Agents orchestration UX route

A dedicated `/agents` route now provides orchestration visibility as a first-class technical workspace.

### UI composition
- summary card (counts + latest status)
- registered agents table
- pipeline control panel (manual triggers)
- recent runs / handoffs / pipeline runs tables

### Integration
- new service boundary: `src/services/agents.ts`
- typed contracts: `src/types/agents.ts`
- links between `/research`, `/prediction`, and `/agents`

### UX constraints
- desktop-first technical layout
- explicit loading/error/empty states
- explicit paper/demo-only messaging
- no autonomous execution controls


## Risk agent refinement (paper/demo only)
- New `apps/backend/apps/risk_agent/` module introduces structured `RiskAssessment`, `RiskSizingDecision`, `PositionWatchRun`, and `PositionWatchEvent`.
- Separation of concerns is explicit: prediction estimates; risk evaluates/sizes; policy authorizes; safety limits; runtime governs mode.
- API endpoints: `POST /api/risk-agent/assess/`, `POST /api/risk-agent/size/`, `POST /api/risk-agent/run-watch/`, `GET /api/risk-agent/assessments/`, `GET /api/risk-agent/watch-events/`, `GET /api/risk-agent/summary/`.
- Frontend route `/risk-agent` provides assessment, sizing, watch loop, and audit history panels.
- Out of scope remains unchanged: no real money, no real execution, no production-grade Kelly optimizer, no exchange stop-loss automation.

## Postmortem board frontend module (new)

Frontend adds `/postmortem-board` with dedicated service/type boundaries:
- `src/services/postmortemBoard.ts`
- `src/types/postmortemBoard.ts`
- `src/pages/PostmortemBoardPage.tsx`

The screen is intentionally operational and auditable (run control, run history, per-perspective panels, final conclusion), and keeps clear empty/loading/error states (including "Generate trade reviews first" guidance).

## Research triage board frontend extension (new)

The `/research` route now combines narrative scan and universe triage board in one operator workspace:

- narrative ingest/analysis controls remain intact
- universe scan controls are added (profile-driven)
- board summary and pursuit candidates are fetched via `services/research.ts`
- triage status badges (`SHORTLISTED`, `WATCH`, `FILTERED_OUT`) and rationale are shown in-table
- prediction handoff action is visible from the board

This avoids adding another route/module while keeping scan → triage → prediction flow explicit.


## Signals opportunity board UX extension

The `/signals` route now acts as a true opportunity board instead of a passive signal list:
- fusion controls + profile selection
- board summary cards by operational status
- ranked opportunity table with rationale and proposal gating hints
- recent fusion run history

This keeps the existing visual language (technical, sober, desktop-first) while improving handoff quality into prediction, market detail, proposals, and operator decisions.

## Opportunities page architecture (new)

`/opportunities` is a thin operational page backed by `services/opportunities.ts`.

It intentionally avoids global state and only composes:
- summary fetch
- cycles fetch
- latest-cycle items fetch
- run-cycle mutation

The page visualizes governance outcomes rather than recomputing them client-side.

## Mission control frontend boundary (new)

The frontend adds `/mission-control` as an explicit operations layer above existing routes.

Responsibilities:
- expose mission loop controls (start/pause/resume/stop/run-cycle)
- surface runtime/safety influence as first-class context
- provide latest-cycle step visibility and recent-cycle KPI table
- connect operators quickly with `/runtime`, `/opportunities`, `/alerts`, `/notifications`

This route intentionally preserves the existing technical, sober UX style and keeps autonomy transparent (no opaque planner UX).

## Portfolio governor UI boundary

Se incorpora `/portfolio-governor` como vista técnica de gobernanza agregada:

- consume `services/portfolioGovernor.ts`
- prioriza trazabilidad (summary cards + throttle block + exposure table + run history)
- mantiene estilo existente (sobrio/técnico/desktop-first)
- refuerza decisiones aguas arriba en `/opportunities` y coordinación con `/mission-control` y `/portfolio`

Esta capa no sustituye la UI de riesgo o lifecycle por posición; complementa la decisión a nivel cartera.

## Adaptive profile manager route

The frontend now includes `/profile-manager` as a dedicated meta-governance page.

Responsibilities:
- trigger backend profile governance runs in explicit modes
- render current regime/decision/constraints with badges and audit context
- provide apply action as explicit operator action (no silent auto-change)
- show recent run history for traceability

Integration is lightweight and uses existing routing + shared API client patterns (`services/profileManager.ts`).


### Execution UI surface
- Added `/execution` route for order lifecycle visibility and control.
- UI consumes `/api/execution/*` to show order/fill status, partials, no-fill outcomes, and summary cards.

## Champion-challenger frontend integration (new)

The `/champion-challenger` route extends existing architecture conventions:

- page-local data loading through `services/championChallenger.ts`
- strongly typed contracts in `types/championChallenger.ts`
- no global state rewrite
- same page sections/components used by prediction/profile/readiness pages

UI flow:
1. show current champion binding
2. configure challenger shadow run
3. render benchmark delta cards + side-by-side table
4. show recent runs with recommendation badges

The page is integrated with lightweight navigation links from `/prediction` and `/profile-manager`.

## Semantic memory UI integration (new)

A new `/memory` route extends the existing operator workspace with a lightweight precedent console.

Frontend additions:
- `src/services/memory.ts` for memory index/retrieve/summary APIs
- `src/types/memory.ts` for typed payloads
- `src/pages/MemoryPage.tsx` for query + results + run history UX

Design intent:
- remain consistent with existing technical/card/table layout
- keep retrieval interactions explicit and auditable
- cross-link with learning/postmortem/prediction/risk routes
- preserve local-first, desktop-first demo ergonomics

## Promotion committee frontend integration (new)

A dedicated `/promotion` route was added using the existing page/service pattern:

- `src/services/promotion.ts`: API boundary for review runs, summary, current recommendation, optional apply
- `src/types/promotion.ts`: typed run/evidence/recommendation contracts
- `src/pages/promotion/PromotionPage.tsx`: manual-first governance UX

UX principles kept:
- strong top recommendation card
- explicit paper/demo-only framing
- inconclusive evidence displayed as governance outcome (not runtime error)
- clear empty/loading/error states
- route-level integration links to champion-challenger, profile-manager, prediction, readiness


## Rollout frontend integration (new)

The frontend now includes a dedicated route `/rollout` for stack promotion operations.

### Data boundary
- `services/rollout.ts` wraps rollout endpoints via existing API client
- `types/rollout.ts` defines plan/run/guardrail/decision structures

### UI boundary
- rollout page is an operator console, not an autonomous controller
- explicit controls only (create/start/pause/resume/rollback)
- explicit empty/loading/error states
- mission control surfaces rollout status for operational awareness

This keeps the architecture consistent with the current desktop-first, auditable, local-first pattern.

## Incident commander frontend integration (new)

A new `/incidents` page is integrated into the same technical desktop-first UX language:

- consumes `services/incidents.ts` over `/api/incidents/*`
- shows degraded mode + active incident summary
- exposes explicit operator actions: run detection, mitigate, resolve
- links to `/mission-control`, `/runtime`, `/rollout`, `/alerts` for cross-module drilldown

This is an orchestration and visibility layer; it does not add autonomous opaque decision logic in the frontend.

## Chaos lab frontend integration (new)

A new route `/chaos` adds resilience validation to the operator workspace using existing UI building blocks.

Frontend integration points:
- `services/chaos.ts` for API calls
- `types/chaos.ts` for typed experiment/run/benchmark payloads
- `pages/chaos/ChaosPage.tsx` for catalog, run controls, runs table, and benchmark cards

UX intent:
- keep design consistent with incidents/mission-control/rollout/runtime pages
- make empty/loading/error states explicit
- expose resilient outcomes even when no incident is created (valid observation)


## Certification board frontend integration

New route: `/certification`.

UI responsibilities:
- display current certification level/recommendation
- show consolidated evidence in one panel (not dispersed across many pages)
- show explicit operating envelope constraints
- show recent run audit trail
- expose manual review trigger with clear loading/error/empty states

Integration pattern:
- new service module: `src/services/certification.ts`
- new types module: `src/types/certification.ts`
- lightweight cross-linking from readiness/chaos/promotion/mission-control/runtime pages

Non-goals remain unchanged: no real execution, no opaque autonomous go-live.


## Broker bridge frontend integration (new)

The `/broker-bridge` route extends the existing technical operations UI without introducing new frontend architecture primitives.

It provides:
- summary cards (created, validated, rejected, dry-run outcomes)
- intent table with validation context
- detail panel for mapping + checks + simulated broker response
- controls to create/validate/dry-run intents

Integration remains lightweight:
- service boundary in `services/brokerBridge.ts`
- type boundary in `types/brokerBridge.ts`
- quick links from `/execution` and `/certification`

## Go-live rehearsal UX

A new `/go-live` route centralizes pre-live readiness at UI level:

- gate state and blocker visibility
- one-click checklist run with persisted result review
- manual approval request workflow
- final rehearsal execution against selected broker intent with clear blocked reasons

This route complements `/broker-bridge` and `/certification` without replacing them.

## Execution venue frontend module (new)

The frontend now includes `/execution-venue` as a technical pre-live contract page.

Responsibilities:
- consume `/api/execution-venue/*` endpoints via `services/executionVenue.ts`
- expose adapter capabilities and sandbox-only warning state
- allow operator-driven build payload / dry-run / parity actions from a selected broker intent
- render canonical payload + normalized response + parity gaps in one workflow
- keep parity gaps visible as valid technical outcomes (not UI failures)

This route complements, but does not replace:
- `/broker-bridge` for intent creation/validation/dry-run
- `/go-live` for checklist/approval/firewall gate state

## Venue account parity UX (new)

The `/venue-account` route extends the existing execution-readiness story:

- `/execution-venue`: outgoing canonical payload + response parity
- `/venue-account`: incoming external-state mirror + reconciliation parity
- `/go-live`: policy/rehearsal/firewall gate

UI contract:
- explicit `SANDBOX_ONLY` warning
- snapshot-first account card
- tabular order/position mirror visibility
- reconciliation panel with parity status and issue list
- no hidden automation; run parity explicitly from operator action

## Connectors UX boundary (new)

A new `/connectors` route exposes adapter qualification and readiness in a sober technical UI:

- readiness card with recommendation + missing capability context
- explicit run controls with fixture selection
- case-level results table with warnings/issues
- recent run history for auditability

The page intentionally links (but does not merge) with `/execution-venue`, `/venue-account`, `/go-live`, and `/certification` to preserve modular boundaries.

## Trace explorer UI boundary (new)

The frontend adds a dedicated `/trace` route to operationalize end-to-end provenance.

Design characteristics:
- snapshot-first audit UX
- explicit query controls by root type/id
- timeline/table readability over heavy graph tooling
- evidence panel unifying precedents/incidents/profile/certification/venue context
- robust loading/error/empty/partial states

Integration style:
- lightweight links from execution/opportunities/venue-account/incidents/memory/mission-control
- no redesign of existing pages
- shared API client and typed service wrapper (`services/trace.ts`)

Scope boundary is unchanged: local-first, single-user, paper/sandbox only.


## Operator cockpit architecture (new)

`/cockpit` is implemented as an aggregation page that **reuses existing module APIs** instead of replacing backend domains.

### Design choices

- Single-pane operational command center for manual-first operation.
- No module rewrite: specialized pages remain authoritative and are linked as drill-down targets.
- Attention model is explicit and deterministic (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`) from runtime/incidents/certification/queue/parity/position/opportunity signals.
- Quick actions call existing control endpoints; cockpit does not introduce a hidden planner.
- Trace integration is link-based (`/trace?root_type=...&root_id=...`) so provenance stays inside trace explorer.

### Partial failure strategy

Cockpit uses per-source fallback in `services/cockpit.ts`:

- each source is fetched independently
- each failure is captured in `snapshot.failures`
- panels keep rendering with available data
- operator sees degraded data explicitly without losing the full view

### Scope boundaries

- keeps local-first, paper/sandbox-only boundaries
- no real-money or live execution
- no multi-user orchestration
- no heavy global state framework introduced



## Runbooks UI

The `/runbooks` page provides the operator workflow surface for runbook instances and templates.

It consumes `/api/runbooks/*` and is integrated lightly with cockpit and incidents:
- Cockpit shows runbook summary and links
- Incidents includes quick link to runbooks
- Runbooks detail links to trace/incidents/queue/mission-control

The page does not duplicate module business logic; it orchestrates existing actions and records outcomes.

## Trust-tiered automation policy UX layer (new)

A new route, `/automation-policy`, provides an operator-facing view of supervised runbook autopilot policies.

### UI composition
- current policy/guardrail posture card
- rule matrix table with trust-tier badges
- recent decision history (`ALLOWED` / `APPROVAL_REQUIRED` / `MANUAL_ONLY` / `BLOCKED`)
- automation action log (`EXECUTED` / `SKIPPED` / `FAILED`)

### Integration pattern
- API integration through `src/services/automationPolicy.ts` using shared `requestJson` client.
- Type-safe payloads in `src/types/automationPolicy.ts`.
- lightweight routing integration through `app/routes.tsx`.
- cross-linking from cockpit and runbooks without redesigning existing pages.

The UX remains manual-first and paper-only, and treats blocked/approval outcomes as healthy governance behavior.

## Runbooks autopilot UI integration (new)

The frontend extends existing runbook pages rather than adding a new standalone orchestration app.

- `services/runbooks.ts` now exposes autopilot run/start/resume/retry/summary APIs.
- `/runbooks` now renders:
  - autopilot summary cards
  - recent autopilot runs
  - approval checkpoints
  - retry/resume controls
  - step outcome evidence
- `/cockpit` consumes autopilot summary for fast operator triage and quick routing.

Design remains technical and sober: explicit states, no opaque planner behavior, and manual-first control posture.

## Approval center frontend integration (new)

The new `/approvals` route extends the existing page/service/type pattern:

- `types/approvals.ts`: normalized request/decision/summary contracts
- `services/approvals.ts`: centralized API client wrappers
- `pages/approvals/ApprovalCenterPage.tsx`: queue + detail operational view

Integration strategy:
- reuse existing shell/components (`PageHeader`, `SectionCard`, `StatusBadge`, `DataStateWrapper`)
- no routing framework rewrite
- cockpit/runbooks add lightweight links and approval-pressure indicators
- trace explorer remains the drill-down system of record


## Trust calibration frontend boundary

Frontend adds `/trust-calibration` as a thin integration page powered by `services/trustCalibration.ts` and `types/trustCalibration.ts`.

The route reuses existing UI primitives (`PageHeader`, `SectionCard`, `StatusBadge`, `DataStateWrapper`) and keeps complexity low:
- no global-state rewrite
- no new websocket/polling subsystem
- no hidden auto-apply behavior

Cross-module integration is lightweight via quick links from automation-policy/approvals/cockpit and evidence drill-down links to trace/approvals pages.

## `/policy-tuning` route (new)

`/policy-tuning` is a dedicated supervised automation tuning board.

- Integrates with trust calibration recommendations and trace evidence.
- Shows actionable policy diff current -> proposed.
- Keeps review/apply flow explicit and audit-oriented.
- Exposes empty/loading/error states for healthy manual-first operation.


## Domain-level autonomy UX layer (new)

The frontend now adds a dedicated domain-level autonomy board at `/autonomy`.

Client boundaries:
- `services/autonomy.ts` for all autonomy API calls
- `types/autonomy.ts` for stage/recommendation/transition contracts
- `pages/autonomy/AutonomyPage.tsx` for manual-first review/apply/rollback flow

UX role:
- complements (not replaces) `/automation-policy` and `/policy-tuning`
- shows domain posture and progressive enablement status
- links evidence and control points to `/trace` and `/approvals`
- surfaces autonomy posture inside cockpit attention/quick-links

State model remains lightweight: page-local fetch orchestration with explicit loading/error/empty handling.

## Autonomy rollout board route

The frontend adds `/autonomy-rollout` as a focused post-change domain-transition monitor:

- follows existing card + table visual language from autonomy/policy-rollout pages
- uses `services/autonomyRollout.ts` with no global state changes
- keeps explicit loading/error/empty states (`REQUIRE_MORE_DATA` treated as normal stabilization)
- integrates via lightweight links from `/autonomy` and `/cockpit`

This extends governance visibility without introducing new orchestration or real-execution capabilities.

## Autonomy roadmap UX architecture (new)

New route: `/autonomy-roadmap`.

It extends existing autonomy governance UX without replacing module boundaries:

- fetches from `services/autonomyRoadmap.ts` (dependencies, plans, run-plan, recommendations, summary)
- composes posture metrics with existing autonomy and autonomy-rollout summaries
- presents recommendation-first sequencing and conflict warnings (`DO_NOT_PROMOTE_IN_PARALLEL`, `REQUIRE_STABILIZATION_FIRST`)
- surfaces optional roadmap bundles and recent plan history

Cockpit integration remains lightweight:
- roadmap summary is added to cockpit snapshot aggregation
- change-governance panel shows roadmap blocked domains + next sequence hints
- quick link and attention item route users to `/autonomy-roadmap`

No routing rewrite or global-state rewrite was introduced.


## Autonomy scenario lab UI (new)

Frontend adds `/autonomy-scenarios` as a dedicated autonomy what-if workspace:

- loaded via `services/autonomyScenario.ts` using existing `services/api/client.ts`
- typed through `types/autonomyScenario.ts`
- technical card/table layout aligned with roadmap/cockpit styling
- explicit loading/error/empty states, including healthy `DO_NOT_EXECUTE` outcomes

Integration points are lightweight and decoupled:
- quick links from autonomy roadmap and cockpit
- trace drill-down from scenario recommendations
- no automatic apply controls and no execution controls on this route


## Autonomy campaign board integration

Frontend now adds `/autonomy-campaigns` as a dedicated execution-program board between roadmap/scenario recommendation pages and operational controls.

- new service layer: `services/autonomyCampaign.ts`
- new types: `types/autonomyCampaign.ts`
- campaign board page with wave/step/checkpoint views
- light integration links from roadmap/scenario/cockpit

The UX remains desktop-first, technical, and conservative: blocked/waiting states are modeled as normal guardrail outcomes.

## Autonomy program frontend architecture (new)

A dedicated route `/autonomy-program` adds a program-control-tower view for multi-campaign governance.

Frontend boundaries:
- `services/autonomyProgram.ts` encapsulates all API calls for program governance endpoints
- `types/autonomyProgram.ts` defines explicit posture/health/recommendation contracts
- `pages/autonomy-program/AutonomyProgramPage.tsx` renders posture cards, health table, recommendations, and rules

UX intent:
- operator-readable, audit-friendly, desktop-first panel
- explicit loading/error/empty states
- safe-state framing: `HOLD_NEW_CAMPAIGNS` and `BLOCKED` can be healthy guardrails

Integration:
- quick links from `/autonomy-campaigns` and `/cockpit`
- context links from recommendations/health to `/approvals` and `/trace`

Non-goals preserved:
- no opaque multi-campaign auto-orchestration UX
- no real-execution UI paths

## Autonomy scheduler frontend route (new)

A new `/autonomy-scheduler` route extends the autonomy control surface without replacing existing pages.

### UI composition
- Header + manual-first safety note.
- Posture/window summary cards.
- Central admission queue table (status, scores, blockers, links, admit/defer actions).
- Recommendation panel with reason codes/blockers/confidence.
- Safe-start windows panel.

### Integration
- Linked from autonomy program/campaign pages and cockpit.
- Uses dedicated API service file (`services/autonomyScheduler.ts`) and typed contracts (`types/autonomyScheduler.ts`).
- Keeps existing route boundaries intact (`autonomy_program` vs `autonomy_campaign` vs `autonomy_scheduler`).


## Autonomy launch UX boundary (new)

A dedicated `/autonomy-launch` route now handles the preflight start-gate workflow for admitted campaigns:

- consume launch API surfaces via `services/autonomyLaunch.ts`
- show explicit readiness and blocker context per campaign
- expose recommendation-first guidance with confidence/reason codes
- keep controls manual-first (`Run preflight`, `Authorize`, `Hold`)
- connect to source-of-truth pages (`/autonomy-scheduler`, `/autonomy-program`, `/autonomy-campaigns`, `/approvals`, `/trace`)

The route follows the existing desktop-first technical card/table style and intentionally avoids introducing a new orchestration UX framework.

## Autonomy activation dispatch board UX boundary (new)

A dedicated `/autonomy-activation` route closes the final gap between authorization and actual campaign start.

Design goals:
- manual-first dispatch (no opaque bulk auto-start)
- explicit revalidation status (`READY_TO_DISPATCH`, `WAITING`, `BLOCKED`, `EXPIRED`)
- visible blockers/reason codes and recommendation rationale
- auditable activation history (`STARTED`, `FAILED`, `BLOCKED`, `EXPIRED`)

Integration points:
- links to `/autonomy-launch`, `/autonomy-scheduler`, `/autonomy-program`, `/autonomy-campaigns`, `/approvals`, `/trace`, `/cockpit`
- service layer in `src/services/autonomyActivation.ts`
- typed payloads in `src/types/autonomyActivation.ts`

## Autonomy operations runtime board (new)

A new route `/autonomy-operations` extends the existing autonomy control chain:
`/autonomy-program` → `/autonomy-scheduler` → `/autonomy-launch` → `/autonomy-activation` → `/autonomy-operations`.

Frontend composition:
- `services/autonomyOperations.ts` for runtime/signals/recommendations/summary/actions
- `types/autonomyOperations.ts` for explicit board payload contracts
- `pages/autonomy-operations/AutonomyOperationsPage.tsx` for manual monitor + acknowledge workflows

UX policy:
- recommendation-only, manual-first
- explicit loading/error/empty states
- no hidden auto-remediation
- trace/approval/campaign deep-linking from runtime and signal panels


### Autonomy interventions board (new)

A dedicated `/autonomy-interventions` page was added as a thin frontend boundary over backend intervention APIs:

- service layer: `services/autonomyInterventions.ts`
- typed payloads: `types/autonomyInterventions.ts`
- route/page: `pages/autonomy-interventions/AutonomyInterventionsPage.tsx`

UI intent:
- show intervention readiness and blockers
- keep actions explicit and operator-driven
- bridge to `/autonomy-campaigns`, `/approvals`, and `/trace` for drill-down
- avoid hidden remediation automation

## Autonomy recovery UX architecture (new)

A dedicated `/autonomy-recovery` route now provides safe-resume governance for affected campaigns.

Composition:
- `services/autonomyRecovery.ts`: typed API gateway for candidates/run-review/snapshots/recommendations/summary
- `types/autonomyRecovery.ts`: explicit status/readiness/recommendation payload contracts
- `pages/autonomy-recovery/AutonomyRecoveryPage.tsx`: manual-first board with summary cards, snapshots table, recommendation panel, and approval request actions

Navigation integration:
- direct links to interventions, operations, program, cockpit, approvals, campaign board, and trace explorer
- cockpit now includes a quick access path to autonomy recovery

Boundary rules in UI:
- no auto-resume or auto-abort controls
- clear empty/loading/error handling
- status badges distinguish `READY_TO_RESUME`, `KEEP_PAUSED`, `BLOCKED`, `REVIEW_ABORT`, `CLOSE_CANDIDATE`, and readiness grades.


## Autonomy disposition UI architecture (new)

A dedicated `/autonomy-disposition` route extends the autonomy governance sequence with final lifecycle disposition controls:

- service boundary: `services/autonomyDisposition.ts`
- type boundary: `types/autonomyDisposition.ts`
- page boundary: `pages/autonomy-disposition/AutonomyDispositionPage.tsx`

UI responsibilities:
- show disposition summary and candidate readiness state
- keep blockers and pending gates visible
- expose recommendation and disposition history panels
- provide manual-first actions (`run review`, `request approval`, `apply`)

Integration remains lightweight through navigation links to campaign, approvals, trace, recovery/interventions, and cockpit without redesigning existing autonomy pages.


## Autonomy closeout board architecture (new)

A dedicated `/autonomy-closeout` route extends the autonomy governance chain after disposition:

- page boundary: `pages/autonomy-closeout/AutonomyCloseoutPage.tsx`
- API client: `services/autonomyCloseout.ts`
- typed payloads: `types/autonomyCloseout.ts`

UI responsibilities:
- show closeout candidate posture (ready vs blocked)
- render auditable report/findings/recommendations panels
- preserve manual-first controls (`Run closeout review`, `Complete closeout`)
- expose trace/approval/campaign navigation without auto-archive or opaque auto-learning

## Followup governance route integration (new)

`/autonomy-followup` is added as a focused post-closeout board:

- consumes new service layer `services/autonomyFollowup.ts`
- keeps page-owned state (no global store rewrite)
- uses existing UI primitives (`PageHeader`, `SectionCard`, `StatusBadge`, `DataStateWrapper`, `EmptyState`)
- links into existing modules (`/autonomy-closeout`, `/approvals`, `/cockpit`, `/trace`, `/autonomy-campaigns`)

The route extends governance visibility without changing the existing manual-first architecture.

## Autonomy feedback frontend surface (new)

The `/autonomy-feedback` route adds a focused governance board for post-followup resolution tracking.

- service boundary: `services/autonomyFeedback.ts`
- typed payloads: `types/autonomyFeedback.ts`
- UI board: `pages/autonomy-feedback/AutonomyFeedbackPage.tsx`

Design intent: connect existing modules (`autonomy-followup`, `autonomy-closeout`, `cockpit`, `approvals`, `trace`) with explicit manual actions and auditable status visibility, without introducing opaque automation or a new client-state framework.

## Autonomy insights frontend architecture (new)

A new page-level module (`/autonomy-insights`) was added without changing the routing model.

### Composition
- Page: `pages/autonomy-insights/AutonomyInsightsPage.tsx`
- Service: `services/autonomyInsights.ts`
- Types: `types/autonomyInsights.ts`

### UX behavior
- explicit loading/error/empty states
- empty state when no lifecycle-closed campaigns are available for synthesis
- manual trigger (`Run insights review`)
- insights and recommendations shown as valid governance states (including `success_pattern` and `REQUIRE_OPERATOR_REVIEW`)
- direct links to campaign/closeout/trace and cockpit integration via quick links

### Scope discipline
- no automatic changes to roadmap/scenario/program/manager flows
- no opaque auto-learning behavior
- still local-first and desktop-first


### Autonomy advisory resolution board UI

`/autonomy-advisory-resolution` extends the autonomy workflow after `/autonomy-advisory` emission:

- fetches candidates/resolutions/recommendations/summary through `services/autonomyAdvisoryResolution.ts`
- exposes manual-first actions (`acknowledge`, `adopt`, `defer`, `reject`)
- keeps empty/loading/error states explicit, including a no-pending-notes message
- adds quick navigation continuity with `/autonomy-advisory`, `/autonomy-insights`, `/cockpit`, and `/trace`

The UI is audit-friendly and intentionally avoids opaque auto-apply behavior.

## Autonomy backlog board frontend architecture (new)

A new route `/autonomy-backlog` is added as the governance backlog handoff surface.

### Composition
- Page: `pages/autonomy-backlog/AutonomyBacklogPage.tsx`
- Service: `services/autonomyBacklog.ts`
- Types: `types/autonomyBacklog.ts`

### UX responsibilities
- show summary cards for candidate/readiness/creation/prioritization posture
- render candidates table with artifact/insight/campaign trace links
- render backlog item history (`backlog_type`, `backlog_status`, `priority_level`, `target_scope`)
- render recommendation queue with rationale/blockers/confidence
- provide explicit manual actions (`Run review`, `Create`, `Prioritize`, `Defer`)
- preserve loading/error/empty states, including: “No adopted autonomy advisories currently require backlog registration.”

### Integrations
- quick navigation from `/autonomy-advisory-resolution` to `/autonomy-backlog`
- cockpit attention includes autonomy backlog pressure/criticality signal
- trace drill-down links to advisory/insight/campaign roots

No opaque auto-apply behavior is introduced in the frontend.


## `/autonomy-intake` frontend route (new)

The frontend now includes `/autonomy-intake` as the governed backlog-to-planning board. It shows intake candidates, proposal history, recommendation feed, and summary metrics while preserving manual-first emission/acknowledgement controls and trace drill-down links.

## `/autonomy-planning-review` frontend layer (new)

La ruta `/autonomy-planning-review` cierra visualmente el loop de planificación iniciado en `/autonomy-intake`.

### Layout
- header técnico con disclaimer manual-first / no opaque auto-apply
- summary cards: emitted, pending, acknowledged, accepted, deferred, rejected
- tabla central de candidates/resolutions con badges de estado
- panel de recommendations con `ACKNOWLEDGE_PROPOSAL`, `MARK_ACCEPTED`, `REQUIRE_MANUAL_REVIEW`, etc.
- acciones manuales: run review, acknowledge, accept, defer, reject

### Navegabilidad
- links directos hacia `trace`, `autonomy-intake`, `autonomy-backlog`, `cockpit`
- drill-down por proposal/backlog/advisory/insight/campaign

### UX states
- loading/error explícitos
- empty state explícito: “No emitted planning proposals currently require resolution tracking.”
- `ACKNOWLEDGED` y `ACCEPTED` mostrados como estados válidos de gobernanza
