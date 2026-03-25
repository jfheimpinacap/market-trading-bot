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
- `services/signals.ts` for signals summary, list, and agents
- `services/proposals.ts` for trade proposal list, detail, and generation endpoints
- `services/paperTrading.ts` for account, positions, trades, snapshots, summary, and revalue
- `services/reviews.ts` for review summary, list, and detail
- `services/riskDemo.ts` for pre-trade assessment
- `services/policy.ts` for trade approval evaluation and policy decision summaries
- `services/experiments.ts` for strategy profiles, experiment runs, and run comparisons

This keeps data dependencies understandable and prevents the current demo phase from turning into a client-state rewrite.

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

- richer review context if backend heuristics expand
- more nuanced market-to-portfolio linking if execution history becomes denser
- optional refresh controls or lightweight polling only if manual/focus refresh becomes insufficient
- deeper system diagnostics without changing the current app shell

## Automation control center

The frontend now includes an `/automation` route backed by `services/automation.ts` and `types/automation.ts`. This page acts as a guided demo control center: it calls the backend automation endpoints through the shared API client, shows loading and error states, renders recent automation runs, and surfaces step-level results for the full demo cycle. The UX is intentionally explicit and operator-driven so the broader end-to-end workflow can move faster without becoming an autonomous system.

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
