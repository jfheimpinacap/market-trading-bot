# Frontend app

Frontend local-first para `market-trading-bot`, construido con React + Vite + TypeScript.

## Qué quedó refinado en esta etapa

El frontend ya no se siente como un conjunto de módulos separados. La UX ahora enfatiza un recorrido demo coherente:

1. **Dashboard** para entender el estado general del sistema demo.
2. **Markets** para descubrir contratos activos.
3. **Signals** como opportunity board real: fusiona research + prediction + risk, rankea oportunidades y explicita proposal gating.
4. **Market detail** para revisar señal, generar proposal demo, evaluar riesgo, evaluar policy engine y ejecutar paper trade sólo cuando la gobernanza demo lo permite.
5. **Proposals** para ver la bandeja de propuestas demo y validar direction, quantity, risk/policy y actionability.
6. **Portfolio** para ver impacto en equity, posiciones y trades.
7. **Positions** para gobernanza de ciclo de vida de posiciones abiertas (hold/reduce/close/review, paper only).
8. **Post-mortem** para revisar outcome, lecciones y volver al market o portfolio.

## Research scan workspace en `/research` (RSS + Reddit + X/Twitter adapter)

La vista `/research` ahora integra narrativa de noticias y narrativa social multi-fuente en un solo flujo:

- panel de fuentes con `RSS`, `REDDIT` y `TWITTER`
- controles separados para `Run ingest`, `Run analysis`, y `Run full research scan`
- tabla de narrative items con tipo de fuente y señal social
- shortlist/candidates con `source_mix` (por ejemplo `NEWS_CONFIRMED`, `MIXED`, `SOCIAL_HEAVY`, `FULL_SIGNAL`)

Todo sigue local-first, auditable y paper/demo only. La integración de X/Twitter es opcional y desacoplada (adapter reemplazable).

## Prediction model governance en `/prediction`

La pantalla `/prediction` ahora incluye una capa de gobernanza de modelo (sin auto-switch):

- **Active model card** con estado actual del runtime (o fallback heurístico)
- **Comparison panel** para ejecutar comparaciones baseline vs candidate por scope y evaluation profile
- **Comparison runs table** con winner + recommendation + trazabilidad temporal
- **Recommendation block** con códigos auditables:
  - `KEEP_HEURISTIC`
  - `KEEP_ACTIVE_MODEL`
  - `ACTIVATE_CANDIDATE`
  - `CAUTION_REVIEW_MANUALLY`

Todo sigue local-first y paper/demo only.

## Exploración de mercados reales (read-only) en frontend

La vista de mercados ahora soporta dos orígenes de datos sin ambigüedad visual:

- **DEMO**: mercados locales/sembrados para flujo de simulación.
- **REAL · READ-ONLY**: mercados ingeridos desde providers reales (ej. Kalshi/Polymarket) solo para exploración.

### Cómo usarlo en UI

1. Ir a `/markets`.
2. En **Source**, elegir:
   - `Demo markets`
   - `Real markets (read-only)`
   - `All sources`
3. (Opcional) filtrar por **Provider** (`Kalshi`, `Polymarket`, etc.).
4. (Opcional) usar **Paper tradable** para separar mercados reales que sí/no permiten paper execution.
4. Abrir `/markets/:marketId` para inspección detallada.

En la tabla, cada row muestra:
- `DEMO` o `REAL · READ-ONLY`
- provider
- estado de paper mode (`Paper-tradable` o `Not paper-tradable`) con razón cuando existe.

### Señales visuales de seguridad operativa

- El listado incluye badges explícitos de **source** y **provider**.
- En market detail de fuente real aparece aviso explícito:
  - `This market uses real read-only data. Any trading in this app remains simulated (paper only).`
- El panel también muestra `execution_mode` y `paper_tradable_reason`.
- El panel de paper trading se mantiene como simulación local; no se habilita ejecución real.
- Si `paper_tradable=false`, la UI bloquea evaluación/ejecución desde el panel y muestra la razón del backend.

### Empty states para real-data

Si no hay mercados reales disponibles al filtrar por `Real markets (read-only)`, la UI guía al operador indicando que primero debe correr la ingesta del backend y luego refrescar.

## Conexiones principales entre pantallas

### `/`
- quick links más enfocados en `Markets`, `Signals`, `Portfolio`, `Post-Mortem` y `System`
- bloque **Current demo flow** con indicadores de:
  - active markets
  - actionable signals
  - open positions
  - recent reviews
- resumen cruzado para que el dashboard explique el flujo completo antes de entrar a un módulo puntual

### `/signals`
- tabla con enlaces más útiles hacia el flujo:
  - abrir market detail
  - evaluar trade cuando la señal es actionable
  - abrir portfolio si ya existe posición ligada
  - abrir post-mortem si ya existe review ligada
- bloque corto de contexto para que Signals funcione como puente y no como módulo aislado

### `/markets/:marketId`
- consolidado como **núcleo operativo** del recorrido demo
- botón **Generate trade proposal**
- panel proposal bridge con thesis, rationale, direction, quantity sugerida, risk/policy, approval_required e is_actionable
- botón **Use proposal suggestion** en el panel de trade para precargar side/type/quantity sugeridos
- workflow summary visible con:
  - señales del market
  - última decisión de riesgo conocida
  - estado de posición abierta
  - latest review si existe
- CTA claros hacia `Portfolio`, `Signals` y `Post-Mortem`
- después de ejecutar un trade, la página refresca contexto de trading y publica un refresh liviano para el resto del flujo

### `/proposals`
- bandeja demo de propuestas en formato tabla desktop-first
- columnas para: market, direction, suggested quantity, proposal score, confidence, policy, actionable, status y created_at
- quick summary superior con total, actionable y latest proposal
- links directos a `market detail` para continuar hacia el panel de trade demo

### `/portfolio`
- posiciones con link claro a market detail
- trades con link claro a review cuando existe
- posiciones y trades muestran badge de source (`DEMO` / `REAL · READ-ONLY`) y `execution_mode`
- bloque corto de reviews recientes
- empty states más guiados hacia `Markets` y `Signals`
- revalue manual refresca la página y también notifica al resto de vistas del flujo

### `/postmortem`
- tabla con workflow links directos a:
  - review detail
  - market detail
  - portfolio
- detail con contexto más legible de:
  - trade setup
  - risk at trade time
  - signal context
  - recommendation / lesson
- cierre más claro del ciclo de navegación

## Recorrido recomendado para probar la demo completa

### Flujo recomendado desde UI

1. Abrir `/` para verificar health, quick links y pipeline summary.
2. Ir a `/signals` para revisar señales demo accionables.
3. Abrir el market asociado desde la señal.
4. En `/markets/:marketId`:
   - revisar chart y señales recientes
   - ejecutar **Evaluate trade** en el panel de risk demo
   - ejecutar el paper trade
5. Ir a `/portfolio` para verificar:
   - posición abierta
   - trade en historial
   - equity / snapshots si ya existen
6. Generar reviews si todavía no existen.
7. Ir a `/postmortem` y abrir la review ligada al trade.
8. Desde la review, volver al market o portfolio usando los links contextuales.

### Acciones manuales que pueden seguir siendo necesarias

Según el estado del entorno local, todavía puede hacer falta ejecutar comandos manuales del backend:

```bash
cd apps/backend && python manage.py seed_paper_account
cd apps/backend && python manage.py generate_demo_signals
cd apps/backend && python manage.py generate_trade_reviews
cd apps/backend && python manage.py refresh_paper_portfolio
```

También puede ser útil correr simulación o revalue para poblar snapshots y mover el historial:

```bash
python start.py simulate-tick
python start.py simulate-loop
```

## Endpoints consumidos por el frontend

### Dashboard
- `GET /api/health/`
- `GET /api/markets/system-summary/`
- `GET /api/markets/`
- `GET /api/signals/summary/`
- `GET /api/signals/`
- `GET /api/reviews/summary/`
- `GET /api/paper/summary/`

### Markets + market detail
- `GET /api/markets/system-summary/`
- `GET /api/markets/providers/`
- `GET /api/markets/events/`
- `GET /api/markets/`
- `GET /api/markets/<id>/`
- `GET /api/signals/?market=<id>`
- `GET /api/reviews/?market=<id>`
- `POST /api/risk/assess-trade/`
- `POST /api/policy/evaluate-trade/`
- `POST /api/paper/trades/`
- `GET /api/paper/account/`
- `GET /api/paper/positions/`
- `GET /api/paper/trades/`
- `GET /api/paper/summary/`
- `POST /api/paper/revalue/`

Query params de markets usados por frontend (sin cliente HTTP paralelo):

- `source_type=demo|real_read_only`
- `provider=<slug>`
- `category=<name>`
- `status=<status>`
- `search=<text>`
- `is_active=true|false`
- `ordering=<field>`

### Signals
- `GET /api/signals/summary/`
- `GET /api/signals/agents/`
- `GET /api/signals/`
- `GET /api/paper/positions/`
- `GET /api/paper/trades/`
- `GET /api/reviews/`

### Proposals
- `GET /api/proposals/`
- `GET /api/proposals/<id>/`
- `POST /api/proposals/generate/`

### Portfolio
- `GET /api/paper/account/`
- `GET /api/paper/positions/`
- `GET /api/paper/trades/`
- `GET /api/paper/summary/`
- `POST /api/paper/revalue/`
- `GET /api/paper/snapshots/`
- `GET /api/reviews/`

### Positions lifecycle
- `POST /api/positions/run-lifecycle/`
- `GET /api/positions/lifecycle-runs/`
- `GET /api/positions/lifecycle-runs/<id>/`
- `GET /api/positions/decisions/`
- `GET /api/positions/summary/`

### Post-mortem
- `GET /api/reviews/`
- `GET /api/reviews/<id>/`
- `GET /api/reviews/summary/`

## Refresh y consistencia entre pantallas

No se agregó estado global sofisticado ni tiempo real.

Sí se agregó un refinamiento pragmático:

- las páginas clave refrescan su contexto al recuperar foco
- Market detail publica un refresh liviano después de ejecutar un trade
- Portfolio publica un refresh liviano después de revalue
- Dashboard, Signals, Portfolio y Post-mortem vuelven a consultar datos cuando el flujo cambia

Con esto la experiencia queda más consistente sin introducir websockets, polling complejo ni una arquitectura nueva.

## Rutas actuales

- `/` — Dashboard operativo local
- `/markets` — Markets explorer
- `/markets/:marketId` — Market detail + risk + policy engine + paper trade
- `/signals` — Demo signals workspace
- `/proposals` — Trade proposal inbox demo
- `/agents` — Agents placeholder
- `/portfolio` — Paper trading portfolio summary
- `/positions` — Position lifecycle manager (hold/reduce/close/review)
- `/postmortem` — Post-mortem trade review queue
- `/postmortem/:reviewId` — Post-mortem review detail
- `/settings` — Settings placeholder
- `/experiments` — Strategy profiles + experiment runner + replay-vs-live comparison
- `/system` — System technical panel

## Variable de entorno

Crea un archivo `.env` en `apps/frontend/` a partir del ejemplo:

```bash
cp .env.example .env
```

Contenido base:

```env
VITE_API_BASE_URL=http://localhost:8000
```

## Flujo recomendado desde la raíz del monorepo

La forma más simple de levantar la UI junto con el backend local es:

```bash
python start.py
```

También puedes usar:

```bash
python start.py up
python start.py --lite
python start.py up --lite
python start.py setup --lite
python start.py setup
python start.py frontend
python start.py status
python start.py down
```

En **lite mode**, el frontend no cambia de arquitectura: sigue apuntando al backend local, pero el backend corre con SQLite y sin requerir Docker/Redis obligatorios. El dashboard y `/system` muestran `app_mode` para distinguir `FULL` vs `LITE`.

## Automation page

The frontend now includes `/automation`, a demo control center for guided local actions.

From this page an operator can:

- run one simulation tick
- generate demo signals
- revalue the paper portfolio
- generate demo trade reviews
- refresh the derived demo state
- run a full demo cycle in sequence

The page is intentionally manual and traceable. It disables controls while an action is running, surfaces success and failure clearly, refreshes recent runs, and keeps the existing end-to-end flow visible:

`market → signal → risk → trade → portfolio → review`

This page does **not** implement autonomous automation, background loops, websockets, or auto-trading.

## Policy engine / approval rules demo

El frontend ahora separa explícitamente dos capas en `/markets/:marketId`:

- **Risk demo**: análisis heurístico del trade.
- **Policy engine**: decisión operativa sobre si el trade demo puede ejecutarse directo, requiere confirmación manual o queda bloqueado.

Flujo UI actual:

1. completar el trade form
2. ejecutar **Evaluate risk**
3. ejecutar **Evaluate policy**
4. según la respuesta:
   - `AUTO_APPROVE` -> habilita ejecución directa
   - `APPROVAL_REQUIRED` -> muestra aviso claro y cambia el CTA a confirmación explícita
   - `HARD_BLOCK` -> mantiene ejecución deshabilitada y sugiere correcciones

La página `/automation` también deja explícito que la automatización demo no opera trades por sí sola y que futuras propuestas automáticas deberían pasar por policy engine primero.


### Semi-auto
- `POST /api/semi-auto/evaluate/`
- `POST /api/semi-auto/run/`
- `GET /api/semi-auto/runs/`
- `GET /api/semi-auto/runs/<id>/`
- `GET /api/semi-auto/pending-approvals/`
- `POST /api/semi-auto/pending-approvals/<id>/approve/`
- `POST /api/semi-auto/pending-approvals/<id>/reject/`
- `GET /api/semi-auto/summary/`


## Continuous demo loop UI

Frontend now includes `/continuous-demo` for autonomous loop operations in paper/demo mode:

- runtime control panel (start/pause/resume/stop/kill-switch/run single cycle)
- current status and active session metrics
- safety panel with active guardrails
- recent cycle history table
- pending approvals snapshot linking to `/semi-auto`

### Continuous demo endpoints consumed
- `POST /api/continuous-demo/start/`
- `POST /api/continuous-demo/stop/`
- `POST /api/continuous-demo/pause/`
- `POST /api/continuous-demo/resume/`
- `POST /api/continuous-demo/run-cycle/`
- `GET /api/continuous-demo/status/`
- `GET /api/continuous-demo/sessions/`
- `GET /api/continuous-demo/sessions/<id>/`
- `GET /api/continuous-demo/cycles/`
- `GET /api/continuous-demo/cycles/<id>/`
- `GET /api/continuous-demo/summary/`


## Safety UI

- New `/safety` route centralizes operational safety state for demo mode.
- Shows current status (`healthy`, `warning`, `cooldown`, `hard-stop`, `kill-switch`), guardrail limits, kill switch controls, and recent safety events.
- Continuous Demo and Semi-Auto pages now surface safety restrictions and disable auto actions when blocked by guardrails.


### /evaluation
Nueva vista técnica para benchmark/evaluación del sistema autónomo paper/demo:

- snapshot actual de auto-execution rate, approval/block rates, review quality, PnL/equity y safety pressure
- tabla de runs recientes comparables
- bloque simple de comparación entre runs recientes
- guidance rule-based (sin ML/LLM) para detectar conservadurismo/agresividad o deterioro de calidad
- estados explícitos de loading/error/empty cuando no hay sesiones evaluables

La pantalla consume: `GET /api/evaluation/summary/` y `GET /api/evaluation/comparison/`.

## Learning Memory UI (new)

Se agregó la ruta `/learning` para visualizar memoria operativa heurística (demo, no ML):

- summary cards de entradas/magnitud conservadora
- tabla de memory entries
- tabla de ajustes activos
- botón de rebuild (`POST /api/learning/rebuild/`)
- explicación explícita de impacto acotado en proposal/risk

Integraciones de navegación:
- quick link desde `/evaluation` a `/learning`
- quick link desde `/postmortem` a `/learning`


## Controlled learning loop UI (new)

Se amplió la UX en rutas existentes, sin rediseño completo:

- `/automation` ahora permite `Rebuild learning memory` y `Run full learning cycle`.
- `/continuous-demo` muestra estado de integración de rebuild automático (conservador y configurable).
- `/learning` incorpora `recent rebuild runs`, estado de integración y trazabilidad de rebuilds.

Mensajes operativos explícitos:
- no ML
- no auto-optimización opaca
- paper/demo only
- rebuild automático desactivado por defecto por seguridad

## Real sync UX integration (new)

Frontend now includes typed real-sync API bindings:
- `src/services/realSync.ts`
- `src/types/realSync.ts`

System + Automation integration:
- `/system` now shows provider sync status, stale/degraded signals, recent sync runs, and manual trigger buttons for provider refresh.
- `/automation` now includes a dedicated `Sync real data (read-only)` action that triggers conservative active-only refresh runs.

The UX keeps the same technical design language: explicit status badges, loading/error/empty states, and no real trading controls.


## Real Ops UI (`/real-ops`)
The frontend now includes a dedicated `/real-ops` route for autonomous real-market paper scope operations.

What it shows:
- explicit safety badges (`REAL`, `READ-ONLY`, `PAPER ONLY`)
- scope configuration summary
- Evaluate and Run controls
- eligible/excluded counters and skip reasons (stale/degraded/no pricing)
- recent run history from backend `RealMarketOperationRun`.

This page does **not** enable real trading or exchange auth.

## Nueva ruta `/allocation`

Se agregó una vista técnica para priorización de ejecución paper:
- control de evaluate/run
- resumen de candidates/selected/reduced/rejected/allocated/remaining
- tabla de propuestas rankeadas con decisión y rationale
- historial de runs persistidos

La vista mantiene el boundary paper/demo only y agrega quick links desde Real Ops/Continuous Demo/Dashboard.

## Operator Queue UI (new)

A new route `/operator-queue` centralizes operator-only exceptions.

It includes:
- summary cards (pending, high priority, approvals/rejections recent, snoozed)
- central queue table with priority/source/type/market/action/status
- detailed context panel with rationale and linked records
- actions: approve and execute, reject, snooze
- explicit loading/error/empty states with positive empty message

The page consumes `src/services/operatorQueue.ts` and remains paper/demo only.

## Replay route (`/replay`)

Se agregó una ruta técnica para historical replay/backtest-like simulation demo:
- panel de control para rango histórico, provider/source scope y market limit
- ejecución de replay sobre snapshots persistidos
- summary de última corrida
- tabla de corridas recientes
- detalle de pasos (`ReplayStep`) para auditoría

Mensajes de estado:
- loading durante ejecución
- empty state: `No replay runs yet.`
- guidance cuando falta histórico: `Sync real market data first to build a usable historical replay.`

La vista mantiene límite estricto: paper/demo only, sin dinero real.


## Experiments workspace (`/experiments`)
Nueva ruta técnica para comparación de perfiles de estrategia en paper/demo mode:

- lista de `StrategyProfile` (tipo, scope, descripción)
- panel para lanzar `replay`, `live_eval` o `live_session_compare`
- tabla de runs recientes con estado y resumen
- comparador A/B entre dos runs con métricas clave y deltas
- mensajes empty/loading/error orientados a ejecutar replay/evaluation antes de comparar

Servicios frontend añadidos:
- `src/services/experiments.ts`
- `src/types/experiments.ts`

## Readiness route (`/readiness`)

Nueva vista técnica para promotion criteria / go-live readiness demo:

- lista de perfiles de readiness (conservative/balanced/strict)
- ejecución manual de assessment por perfil
- summary claro de `READY` / `CAUTION` / `NOT_READY`
- tabla de gates fallidos (expected vs actual + reason)
- recomendaciones operativas explícitas
- historial reciente de readiness runs

Mensajes de empty state orientan al operador a correr primero evaluation/replay/experiments.

Importante: `/readiness` es solo evaluación formal y **no activa dinero real ni ejecución real**.

## Runtime governance route (`/runtime`) (new)

Frontend now includes `/runtime` to operate and audit explicit runtime governance.

The page shows:
- current mode and effective status
- readiness and safety influence
- mode selector with blocked reasons
- effective capabilities for the active mode
- recent transition history

Frontend service bindings:
- `src/services/runtime.ts`
- `src/types/runtime.ts`

Important scope note:
- this is still paper/demo only and does not enable real-money execution.

## Operator alerts UI (`/alerts`)

Frontend now includes an **Operator Alerts** page that consolidates:
- active alert summary cards
- deduplicated open-alert table
- alert detail panel with metadata and operator actions (acknowledge/resolve)
- recent digest list

Supporting modules:
- `src/services/alerts.ts`
- `src/types/alerts.ts`
- `src/pages/alerts/AlertsPage.tsx`

This view is technical, desktop-first, and aligned with runtime/safety/operator-queue workflows.

## Notifications route (`/notifications`)

Nueva vista técnica para delivery outbound de alertas/digests paper-demo:

- cards de resumen (health, sent/failed/suppressed)
- panel de channels
- panel de rules
- historial de deliveries con status badges
- acciones manuales: enviar último alert abierto y último digest

Servicios frontend añadidos:
- `src/services/notifications.ts`
- `src/types/notifications.ts`

La vista mantiene estados de loading/error/empty y no introduce realtime ni mensajería enterprise.

## Notifications automation UX (new)

`/notifications` now includes:
- automation status card (global + dispatch/digest/escalation flags)
- control panel (enable/disable automation, run automatic dispatch, run digest cycle)
- delivery history with explicit trigger badges (`MANUAL`, `AUTOMATIC`, `DIGEST_AUTOMATION`, `ESCALATION`)
- recent escalations table and empty-state messaging

The page remains technical, desktop-first, and consistent with alerts/runtime/safety modules.

## Research route (`/research`)

A new technical route adds the first narrative scan/research workspace:

- source panel for configured RSS feeds
- run controls for ingest + analysis
- recent narrative items table (sentiment/confidence/link count)
- research shortlist table with market direction vs implied direction + divergence/alignment tags
- explicit degraded mode messaging when local LLM is unavailable

Data bindings:
- `src/services/research.ts`
- `src/types/research.ts`
- route page: `src/pages/ResearchPage.tsx`

## Prediction UI (`/prediction`)

Se agregó una ruta técnica `/prediction` con:
- panel de profiles
- scoring form (market + profile)
- result card (`system_probability`, `market_probability`, `edge`, `confidence`, `rationale`)
- tabla de recent scores

También se agregó integración ligera desde `/research`:
- quick link a `/prediction`
- acción por candidate: `Score in prediction agent`

Todo sigue en modo local-first paper/demo.

## Prediction page enhancements (training + registry)

`/prediction` now includes a technical training panel to support local model lifecycle operations:

- build historical dataset
- trigger XGBoost training run
- inspect recent training runs and validation summary
- inspect model artifacts and activate an artifact for runtime
- clear runtime message when heuristic fallback is in use

The page remains desktop-first, auditable, and aligned with paper/demo constraints.

## Agents route (`/agents`)

The frontend now includes a real orchestration workspace at `/agents`.

### Includes
- orchestration header with explicit paper/demo-only boundary
- registered agents panel
- pipeline controls:
  - Research → Prediction
  - Postmortem → Learning
  - Real-market agent cycle (read-only scope + paper/demo risk outputs)
- recent agent runs table
- recent handoffs table
- recent pipeline runs table

### Data/services
- `src/services/agents.ts`
- `src/types/agents.ts`
- backend endpoints under `/api/agents/*`

### UX behavior
- explicit loading/error states
- clear empty states (e.g. “Run a pipeline to see agent handoffs.”)
- conservative technical styling aligned with research/prediction/runtime pages
- quick links between `/research`, `/prediction`, and `/agents`


## Risk agent refinement (paper/demo only)
- New `apps/backend/apps/risk_agent/` module introduces structured `RiskAssessment`, `RiskSizingDecision`, `PositionWatchRun`, and `PositionWatchEvent`.
- Separation of concerns is explicit: prediction estimates; risk evaluates/sizes; policy authorizes; safety limits; runtime governs mode.
- API endpoints: `POST /api/risk-agent/assess/`, `POST /api/risk-agent/size/`, `POST /api/risk-agent/run-watch/`, `GET /api/risk-agent/assessments/`, `GET /api/risk-agent/watch-events/`, `GET /api/risk-agent/summary/`.
- Frontend route `/risk-agent` provides assessment, sizing, watch loop, and audit history panels.
- Out of scope remains unchanged: no real money, no real execution, no production-grade Kelly optimizer, no exchange stop-loss automation.

## Postmortem board route (new)

New route: `/postmortem-board`.

UI sections:
- board summary cards
- run board panel (select trade review + run)
- recent board runs table
- perspective review panels with status/confidence/action items
- final structured board conclusion

The route is integrated with `/postmortem`, `/learning`, and `/agents` through quick links and pipeline controls.

## Triage board UX in `/research` (new)

`/research` now includes a universe scanner + triage board without creating a new route:

- universe scan controls (`profile` + `Run universe scan`)
- board summary cards (considered / filtered / shortlisted / watchlist + top exclusions)
- pursuit candidates table with triage status, score, tradability metrics, narrative context, and actions
- triage-to-prediction action that bridges to agent orchestration
- explicit empty states: "Run a universe scan to triage markets."

All behavior remains local-first and paper/demo only.


## Opportunity board en `/signals` (nuevo foco)

La ruta `/signals` ahora funciona como tablero operativo de oportunidades:

- control de `Run signal fusion` con perfil (`conservative`, `balanced`, `aggressive light`)
- summary cards por estado (`WATCH`, `CANDIDATE`, `PROPOSAL_READY`, `BLOCKED`)
- tabla central con edge, confidence, risk, score, status, rationale y acciones
- historial de runs recientes
- degradación explícita para loading/error/empty states

Todo se mantiene local-first y paper/demo only.

## Opportunities supervisor UI (new)

New route: `/opportunities`

Provides:
- run controls for the opportunity cycle (with profile selection)
- summary cards for built/queued/auto/block/proposal-ready counts
- latest cycle item trace table from signal context to final execution path
- recent cycle history
- quick links to `/proposals` and `/operator-queue`

The route is explicitly paper/demo-only and does not enable real-money execution.

## Mission control UI (new)

The frontend now includes `/mission-control` as the autonomous operations cockpit:
- start/pause/resume/stop/run-cycle controls
- runtime + safety influence visibility
- latest cycle step breakdown (research/opportunity/watch/alerts/notifications/digest/...)
- recent cycle outcomes table (queue/auto/blocked)
- quick navigation links to Runtime, Opportunities, Alerts, and Notifications

This route remains paper/demo only and intentionally operator-auditable.

## Portfolio governor route

Nueva ruta `/portfolio-governor`:

- ejecutar governance review con profile selector
- ver summary cards de exposición/concentración/throttle/drawdown
- inspeccionar exposición por market/provider/category
- ver bloque de throttle decision con rationale y reason codes
- revisar historial de governance runs

Integraciones ligeras:
- quick links desde `/portfolio`, `/mission-control` y `/opportunities`
- `/opportunities` muestra estado de throttle actual y alerta visible cuando hay `BLOCK_NEW_ENTRIES`
