# Frontend app

Frontend local-first para `market-trading-bot`, construido con React + Vite + TypeScript.

## Precedent-aware UX (new)

La UI ahora expone señales de memoria histórica sin sobrecargar pantallas:

- `/research`: shortlist con `PRECEDENT_AWARE` + warnings históricos.
- `/prediction`: tabla de scores con contexto de precedente e influencia.
- `/risk-agent`: latest assessment incluye cautela basada en historial.
- `/postmortem-board`: muestra casos/fallos previos similares dentro de la conclusión.
- `/memory`: audit trail de `precedent uses` + influencia reciente.

Todo mantiene límites explícitos: paper/demo only, sin ejecución real, y sin LLM como autoridad final.

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


## Operator cockpit en `/cockpit` (new)

Se agregó un **operator cockpit / command center** como home técnico de operación manual-first.

Qué centraliza en una sola vista:

- postura del sistema: runtime, degraded mode, certification, profile regime
- mission control + incidents operativos
- riesgo/exposure: portfolio governor, throttle, review_required
- ejecución/venue: broker bridge, parity, venue reconciliation
- change governance: promotion, rollout, champion/challenger
- attention queue priorizada por severidad con drill-down a módulos y a `/trace`
- quick actions para disparar acciones ya existentes (sin nueva lógica autónoma)

Diseño y alcance:

- desktop-first, sobrio, auditable
- no reemplaza pantallas especializadas; las enlaza como source of truth
- fallback parcial por panel cuando algún endpoint falla
- local-first, single-user, paper/sandbox only

### Endpoints integrados por cockpit

El cockpit compone servicios ya existentes (sin backend monolítico nuevo):

- runtime, incidents, mission-control
- rollout, certification, profile-manager
- portfolio-governor, positions, opportunities
- broker-bridge, execution-venue, venue-account
- operator-queue, alerts
- promotion, champion-challenger
- trace summary + query runs

## Autonomy advisory board en `/autonomy-advisory` (new)

Se agregó una vista formal de emisión advisory para cerrar el loop entre insights y artefactos manuales auditables:

- summary cards de candidates/ready/blocked/emitted/duplicate-skipped + notas por target
- tabla central de candidates con blockers, artifact existente y acciones de emisión manual
- historial de advisory artifacts con estado, target, vínculos y rationale
- panel de recomendaciones advisory (emit/skip/manual-review/reorder)
- quick links a `/autonomy-insights`, `/autonomy-feedback`, `/autonomy-closeout`, `/cockpit` y `/trace`

Límites se mantienen explícitos: recommendation-first, manual-first, local-first, paper/sandbox only; sin auto-apply opaco.

## Policy rollout monitor en `/policy-rollout` (new)

Nueva ruta técnica para cerrar el loop post-change de automation policy tuning:

- arranca monitoreo desde un candidato `APPLIED` de `/policy-tuning`
- muestra `baseline` vs `post-change` con deltas explícitos
- presenta recommendation panel (`KEEP_CHANGE`, `REQUIRE_MORE_DATA`, `ROLLBACK_CHANGE`, etc.)
- expone rollback manual asistido (sin auto-rollback opaco)
- integra navegación con `/policy-tuning`, `/trust-calibration`, `/approvals`, `/trace` y señales en `/cockpit`

Estados UX incluidos:
- loading/error explícitos
- empty state claro para runs vacíos:
  - `Start a rollout monitor from an applied policy tuning change.`
- `REQUIRE_MORE_DATA` mostrado como resultado sano de gobernanza (no como error)

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

## Execution-aware UX (replay / evaluation / experiments / readiness)

Se agregó una capa visual para execution realism sin crear rutas gigantes nuevas:

- `/replay`:
  - selector `execution_mode` (`naive` vs `execution_aware`)
  - selector `execution_profile` (`optimistic_paper`, `balanced_paper`, `conservative_paper`)
  - métricas de fill/no-fill/partial/slippage y execution drag cuando hay evidencia
  - empty state explícito: “Run replay with execution-aware mode to measure fill realism.”
- `/evaluation`:
  - bloque técnico “Execution-aware impact” con métricas ajustadas por ejecución
- `/experiments`:
  - permite lanzar runs con execution mode/profile
  - comparación muestra deltas naive vs aware cuando aplica
- `/readiness`:
  - bloque “Execution realism impact” mostrando penalización de readiness por calidad de ejecución

Todo se mantiene desktop-first, sobrio, auditable, local-first y paper/demo only.

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

## Meta-governance UI: `/profile-manager`

New technical route `/profile-manager` adds an auditable adaptive profile control panel:

- run governance (recommend/apply modes)
- view current regime and blocking constraints
- inspect current decision rationale + reason codes + target module profiles
- inspect recent governance runs

This route integrates with Portfolio Governor, Mission Control, Runtime, and Opportunities via quick links and keeps explicit paper/demo-only messaging.


## Execution route
- New `/execution` page provides paper execution realism visibility: order lifecycle states, fills, summary metrics, and lifecycle controls.
- Uses `src/services/execution.ts` and remains paper/demo only.

## Champion-Challenger route (new)

The frontend now includes `/champion-challenger` as a technical benchmark workspace for shadow comparisons:

- champion binding summary card
- challenger run panel (lookback + execution profile)
- key delta cards (opportunities/proposals/fill-rate/execution-adjusted pnl/recommendation)
- side-by-side comparison table
- recent run history with recommendation badges
- clear empty/loading/error states with paper/demo-only messaging

The page is integrated via quick links from `/prediction` and `/profile-manager`.

This route is evidence-oriented only; it does not auto-switch active stack.

## Semantic memory workspace en `/memory` (nuevo)

La UI ahora incluye `/memory` como capa formal de precedentes semánticos para paper/demo:

- cards de estado (`documents indexed`, `retrieval runs`, `types present`, `last indexing`)
- panel de consulta (`query text`, `query type`, `run retrieval`)
- tabla de precedentes recuperados (rank, tipo, título, similitud, razón, fuente)
- historial reciente de retrieval runs
- estados claros de loading/error/empty

Integración operativa:
- enlaces directos a `/learning`, `/postmortem-board`, `/prediction` y `/risk-agent`
- mensaje explícito cuando falta indexado inicial: “Index learning and review documents first.”
- “no good match” tratado como resultado válido y no como error

## Promotion committee UI (new)

New route: `/promotion`

The page provides:
- current recommendation card (code, confidence, rationale, blockers)
- consolidated evidence summary (execution-aware metrics, readiness, governance context)
- run-review panel with recommendation-only default
- explicit manual apply control (only when allowed by backend)
- recent review run audit table

Integration links were added from:
- `/champion-challenger`
- `/profile-manager`

All remains local-first, single-user, and paper/demo only.


## Rollout UI (new)

A new `/rollout` route provides the operator UI for formal canary promotion and rollback guardrails.

Included UI blocks:
- header with paper/demo-only boundary
- current rollout card (mode, percentage, phase, status)
- controls (create plan, start/pause/resume, rollback)
- guardrail summary and latest rollout recommendation
- recent runs table with distribution counters

Frontend integration:
- `src/services/rollout.ts`
- `src/types/rollout.ts`
- route links from `/promotion`, `/champion-challenger`, and `/mission-control`

## Incident commander UI (new)

Route `/incidents` provides a dedicated operational resilience view:
- current degraded mode state card
- incident table with severity/status/source/traceability
- detail panel with mitigation and recovery history
- operator controls for detection, mitigation, and resolution

This complements (not replaces) `/alerts`, `/runtime`, `/mission-control`, and `/rollout`.

## Chaos Lab UI (new)

The frontend now includes `/chaos`, a dedicated resilience workspace to run controlled fault-injection experiments and inspect resilience evidence.

The page includes:
- experiment catalog (target module, severity, description)
- manual run controls
- recent run table with status badges
- benchmark panel for detection/mitigation/recovery plus degraded/rollback flags

It is explicitly paper/demo only and links directly to `/incidents`, `/mission-control`, `/runtime`, and `/rollout`.


## Operational certification UX (`/certification`)

The frontend now includes `/certification` as the formal operational certification board for paper/demo autonomy.

It provides:
- current certification card (level, recommendation, confidence, rationale)
- consolidated evidence panel (readiness, chaos, evaluation, incidents, rollout/promotion)
- explicit operating envelope panel (autonomy, entries, sizing, profile constraints)
- recent certification runs table
- manual-first review trigger (`Run certification review`)

Integration links were added from readiness, chaos, promotion, mission-control, and runtime pages.

This remains paper/demo only and does not enable real execution.


## Broker bridge UI (new)

A new `/broker-bridge` route adds a technical paper-only bridge console:

- create broker intents from execution-ready paper orders
- validate intents against backend guardrails
- run dry-run simulated routing
- inspect validation checks, blocking reasons, missing fields, mapping profile, and simulated response

The UI is explicitly labeled **paper-only** and does not trigger any real broker communication.

## /go-live route (paper-only rehearsal)

Frontend now includes `/go-live`, a dedicated go-live rehearsal page that shows:

- current gate state + firewall status
- checklist controls/results
- manual approval request panel
- final rehearsal panel on top of broker intents

The page is intentionally explicit that **real orders are still disabled** and firewall blocking is expected/healthy in this phase.

## Execution Venue UI (new)

Nueva ruta: `/execution-venue`.

Objetivo UX:
- mostrar el contrato canónico de venue/adapters sin tocar live
- visualizar capacidades del adapter actual (`null_sandbox`)
- construir payload desde `BrokerOrderIntent`
- simular `dry-run` bajo contrato uniforme
- ejecutar parity harness y revisar gaps como resultado técnico válido

Integraciones ligeras:
- links rápidos desde `/broker-bridge` y `/go-live`
- estado explícito `SANDBOX_ONLY`
- mensaje claro cuando no existen intents: “Create a broker intent first to test venue parity.”

## Venue Account Mirror UI (new)

A new operator page is available at `/venue-account`.

It provides:
- sandbox boundary warning (`SANDBOX_ONLY`)
- current external-style account snapshot (equity/cash/reserved/open counts)
- external order snapshots table
- external position snapshots table
- reconciliation controls + recent runs/issues

The page is intentionally technical and conservative. Parity gaps are displayed as valid reconciliation results (not treated as frontend failures).

## Connectors route (`/connectors`) (new)

The frontend now includes a dedicated **Connectors** route for venue adapter qualification and readiness.

What it shows:
- explicit sandbox-only warning banner
- current adapter readiness recommendation card
- fixture-based qualification run controls
- latest qualification case results (issues/warnings visible as valid technical outcomes)
- recent run history with status + recommendation badges

Integration links are kept light and consistent with `/execution-venue`, `/venue-account`, `/go-live`, and `/certification`.

Non-goals remain unchanged:
- no real broker connections
- no credentials
- no live/read-only third-party connectivity yet
- no real orders/money

## `/trace` route (new)

A new `/trace` route provides a unified decision provenance and audit explorer.

It includes:
- root query panel (`root_type` + id)
- provenance snapshot card (status, key stages, blockers, execution outcome, incident/degraded context)
- trace timeline table with stage badges
- related evidence panel (precedents/incidents/profile/certification/venue context)
- auditable recent query-run history

Client boundary:
- service: `src/services/trace.ts`
- types: `src/types/trace.ts`
- route: `src/pages/TracePage.tsx`

This route is explicitly local-first and paper/sandbox-only.


## /runbooks

The frontend includes a `/runbooks` page for guided operator remediation workflows.

It shows:
- Summary cards (open / in progress / blocked / completed / escalated)
- Active runbooks with next steps
- Template catalog with create actions
- Step-by-step runbook detail with result history
- Deterministic recommendations and links to `/cockpit`, `/incidents`, `/trace`, `/mission-control`, and `/operator-queue`

This view is manual-first and paper/sandbox only.

## Automation policy workspace `/automation-policy` (new)

A dedicated route now surfaces trust-tiered supervised automation over existing runbook/operational actions.

What the page shows:
- active automation profile and guardrail influence (runtime/safety/certification/degraded mode)
- rule matrix with action types, trust tiers, and rationale
- recent decisions (`ALLOWED`, `APPROVAL_REQUIRED`, `MANUAL_ONLY`, `BLOCKED`)
- auto-action log (`EXECUTED`, `SKIPPED`, `FAILED`)
- explicit manual-first/paper-only framing and profile switching controls

Frontend integration points:
- service layer: `src/services/automationPolicy.ts`
- types: `src/types/automationPolicy.ts`
- route: `/automation-policy`
- quick links added from cockpit and runbooks flows

Scope remains conservative:
- no real-money paths
- no real execution
- no opaque autonomous planner

## Runbooks supervised autopilot UX (new)

`/runbooks` now includes supervised autopilot controls and audit surfaces:

- `Run autopilot` action per runbook
- autopilot run status badges (`RUNNING`, `PAUSED_FOR_APPROVAL`, `BLOCKED`, `COMPLETED`, `FAILED`, `ABORTED`)
- approval checkpoints with explicit approve-and-resume flow
- step-level outcomes (`AUTO_EXECUTED`, `APPROVAL_REQUIRED`, `MANUAL_ONLY`, `BLOCKED`, `FAILED`, `SKIPPED`)
- retry controls for failed/blocked steps
- empty/loading/error states for autopilot runs and summaries

`/cockpit` now also surfaces autopilot paused/blocked posture and attention item routing back to `/runbooks`.

Scope is unchanged: local-first, single-user, paper/sandbox only, manual-first supervision.

## Approval Center UI (new)

The frontend now includes `/approvals` as the unified human decision gate tray.

Implemented UX:
- header with manual-first scope reminder
- summary cards (pending, high priority, approved recently, expired/escalated)
- centralized approval queue table (source, title, priority, status, requested time, impact preview, trace link)
- detail panel with rationale/context, impact preview, evidence hints, and approve/reject/expire/escalate controls
- explicit empty/loading/error states

Integration points:
- quick links from cockpit/runbooks
- cockpit now surfaces pending approval pressure
- trace deep links from each approval row/detail item


## Trust calibration UX

A new route `/trust-calibration` adds a formal approval analytics / trust-calibration view that integrates with existing pages (`/automation-policy`, `/approvals`, `/runbooks`, `/cockpit`, `/trace`).

Highlights:
- recommendation-only + manual-first header messaging
- summary cards (actions analyzed, friction, top domains, recommendation count)
- action-level metrics table with current tier and recommendation badge
- recommendation panel with current→recommended tier, reason codes, confidence, and evidence links
- recent run history for auditable evolution
- explicit empty-state for insufficient evidence (`Not enough approval/autopilot history yet to calibrate trust tiers.`)

## Policy tuning board en `/policy-tuning` (new)

Se agregó una vista técnica y auditable para supervised automation tuning:

- lista de tuning candidates (status, trust-tier diff, confianza)
- panel de diff current vs proposed (tier + conditions)
- review controls explícitos (`APPROVE`, `REJECT`, `REQUIRE_MORE_EVIDENCE`, `DEFER`)
- apply manual solo para candidatos `APPROVED`
- logs before/after visibles

La ruta conserva límites explícitos: local-first, single-user, paper/sandbox only, sin auto-apply.


## Autonomy stage manager UI in `/autonomy` (new)

A new `/autonomy` route adds the progressive enablement board for domain-level autonomy envelopes.

It provides:
- domain state cards and stage/status badges
- recommendation panel (`promote`, `keep`, `downgrade`, `freeze`, `require_more_data`, `rollback`)
- transition controls for manual apply and manual rollback
- evidence links toward `/trace` and `/approvals`
- summary cards for manual/assisted/supervised/frozen/degraded posture

Integration:
- connects with `/automation-policy`, `/trust-calibration`, `/policy-tuning`, `/policy-rollout`, `/cockpit`, and `/trace`
- keeps action-level policy authority in automation policy
- keeps domain-level stage transitions explicit and auditable

Deliberate non-goals remain: no real-money execution, no real execution venue routing, no opaque auto-promotion.

### Autonomy rollout monitor (new)

A new route `/autonomy-rollout` provides the domain transition post-change board:

- start monitor from an already applied autonomy transition
- active rollout status + recommendation badge
- baseline vs post-change metrics and deltas
- recommendation panel with rationale, warnings, cross-domain notes
- manual rollback controls (approval-oriented)
- recent run history

Frontend integration points:
- new service `src/services/autonomyRollout.ts`
- new types `src/types/autonomyRollout.ts`
- quick links from `/autonomy` and `/cockpit`

## Autonomy roadmap board en `/autonomy-roadmap` (new)

Se agregó una nueva ruta técnica para gobierno global de autonomía entre dominios:

- postura global (manual/assisted/supervised + blocked/frozen/under observation)
- panel de recomendaciones (`NEXT_BEST_MOVE`, secuencia sugerida, bloqueos)
- vista de dependencias (`requires_stable`, `incompatible_parallel`, etc.)
- bundles recomendados con riesgo y `requires_approval`
- tabla de planes recientes auditables

Integraciones ligeras:
- quick links desde `/autonomy` y `/cockpit`
- navegación a `/trace`, `/approvals`, `/autonomy`, `/autonomy-rollout`
- estado vacío explícito: `Run an autonomy roadmap review to coordinate domain progression.`


## Autonomy scenarios UI (new)

Added route `/autonomy-scenarios` as a simulation-only lab to compare autonomy progression alternatives before any manual apply step.

UI sections:
- options panel (single/sequence/bundle/freeze-delay candidates)
- risk panel (dependency conflicts, friction, degraded/incident exposure, approval-heavy)
- recommendation panel (best/safe/delay/do-not-execute outputs)
- recent run history with selected option and recommendation summary

This route is integrated with `/autonomy-roadmap`, `/autonomy`, `/approvals`, `/cockpit`, and `/trace` through lightweight navigation links.


## Autonomy campaigns UI (new)

Added `/autonomy-campaigns` as the staged scenario-to-execution handoff board:

- campaign cards with status/source/wave/progress
- detailed wave/step timeline
- checkpoint table (approval + observation gates)
- controls for create/start/resume/abort
- explicit empty/loading/error states
- cockpit + roadmap + scenario quick-link integration

This page stays manual-first and recommendation-first, and does not introduce real execution.

## Autonomy program UI en `/autonomy-program` (new)

Nueva vista técnica para gobierno global de campañas de autonomía:

- cards de postura global (`active`, `blocked`, `observing`, `waiting approvals`, `concurrency posture`)
- panel de health por campaña con score, blockers e influencia de incident/degraded/rollout
- panel de recommendations (`continue/pause/reorder/hold/wait`) con rationale + confidence
- panel de reglas de concurrencia activas
- acción explícita `Run program review` (manual-first)

Integraciones ligeras:
- quick link desde `/autonomy-campaigns`
- quick link desde `/cockpit`
- enlaces contextuales hacia `/approvals` y `/trace`

Se mantiene el mismo boundary:
- sin auto-orquestación opaca multi-campaña
- sin dinero real ni ejecución real
- single-user local-first

## Autonomy scheduler UI (new)

The frontend now includes `/autonomy-scheduler` as a dedicated campaign-admission board.

Key UX sections:
- posture + active window cards
- candidate queue table with blockers and manual admit/defer actions
- recommendation stream (`WAIT_FOR_WINDOW`, `SAFE_TO_ADMIT_NEXT`, `BLOCK_ADMISSION`, etc.)
- safe-start windows panel

Service integration:
- `src/services/autonomyScheduler.ts`
- `src/types/autonomyScheduler.ts`

Route boundary:
- `autonomy_program` remains active-campaign coexistence control
- `autonomy_scheduler` governs pending campaign admission ordering and safe-start windows
- no opaque auto-start is introduced


## Autonomy launch board en `/autonomy-launch` (new)

Nueva ruta técnica para control de inicio manual-first entre admission y start de campañas:

- cards de postura/resumen (`ready`, `approval-required`, `blocked`, `waiting`)
- panel de candidatos con readiness status, blockers y pendientes
- panel de recomendaciones (`START_NOW`, `WAIT_FOR_WINDOW`, `BLOCK_START`, etc.)
- panel de autorizaciones recientes (estado, approval linkage, expiración)
- acciones explícitas: `Run preflight`, `Authorize`, `Hold`

Integración ligera incluida con `/autonomy-scheduler`, `/autonomy-program`, `/autonomy-campaigns`, `/cockpit`, `/approvals` y `/trace`.

## Autonomy activation board en `/autonomy-activation` (new)

Se agrega una vista de dispatch manual-first para cerrar el ciclo `launch authorization -> campaign start` sin reemplazar `autonomy_launch`, `autonomy_scheduler`, `autonomy_program` ni `autonomy_campaign`.

Incluye:
- summary cards de readiness/blocked/expired/started/failed
- panel de candidates autorizados con blockers y links a campaign/approvals/trace
- panel de recomendaciones (`DISPATCH_NOW`, `BLOCK_DISPATCH`, `WAIT_FOR_WINDOW`, etc.)
- historial de activaciones con estados auditable (`STARTED`, `BLOCKED`, `FAILED`, `EXPIRED`)
- acciones explícitas: `Run dispatch review` y `Dispatch`

Servicios nuevos:
- `src/services/autonomyActivation.ts`
- endpoints `/api/autonomy-activation/*`

Integración ligera:
- quick links desde `/autonomy-launch`, `/autonomy-scheduler` y cockpit hacia `/autonomy-activation`.

## Autonomy operations board en `/autonomy-operations` (new)

Nueva ruta técnica para supervisar campañas de autonomía activas en runtime.

Incluye:
- header operativo con recordatorio manual-first
- summary cards: active/on-track/stalled/blocked/waiting-approval/observing/open-signals
- runtime table con wave/step/checkpoint/last-progress/stall/blockers
- panel de attention signals (`OPEN`, `ACKNOWLEDGED`) con acción **Acknowledge**
- panel de recomendaciones (`CONTINUE_CAMPAIGN`, `PAUSE_CAMPAIGN`, `ESCALATE_TO_APPROVAL`, `REVIEW_FOR_ABORT`, etc.)
- botón manual **Run monitor**

Integración ligera:
- enlace rápido desde `/autonomy-activation`
- enlace rápido desde `/cockpit`
- links por fila hacia `/autonomy-campaigns`, `/approvals` y `/trace`

Estado UX:
- loading/error explícitos
- empty state explícito para ausencia de campañas activas
- `ON_TRACK` y `ACKNOWLEDGED` visibles como estados válidos
- sin auto-remediación opaca


## Autonomy interventions in `/autonomy-interventions` (new)

New route `/autonomy-interventions` provides an active campaign action board for manual-first operational remediation.

Includes:
- summary cards: open/approval-required/ready/blocked/recent actions/campaigns needing intervention
- requests table: campaign, action, source, severity, blockers, rationale, reason codes, and links to campaign/approvals/trace
- action history: executed_by, executed_at, result summary, failure message
- explicit controls: run intervention review, create manual request, execute request, cancel request

Scope guardrails remain explicit: paper/sandbox only, manual-first, and no opaque auto-remediation.

## Autonomy recovery route in `/autonomy-recovery` (new)

New operator board for paused/blocked campaign resolution and safe-resume governance.

What it shows:
- summary cards (candidates, ready, keep paused, blocked, review abort, close candidate)
- recovery snapshots table (blockers, pending approvals/checkpoints, pressure, readiness/status)
- recovery recommendations panel (resume/keep paused/recovery needed/review abort/close/reorder)
- manual-first action panel to request resume/close approvals

UX boundaries:
- no opaque auto-resume and no auto-abort
- `READY_TO_RESUME` and `KEEP_PAUSED` are valid, expected states
- explicit loading, error, and empty states

Integration links:
- connected to interventions, operations, campaigns, approvals, cockpit, and trace explorer.


## Autonomy disposition board en `/autonomy-disposition` (new)

Nueva vista técnica para governanza de cierre/retire final de campañas:

- summary cards (candidates, ready-to-close/abort/retire, review, approvals)
- candidates table con readiness, blockers, gates y recomendación
- recommendations panel y dispositions history auditables
- acciones manual-first: `Run disposition review`, `Request approval`, `Apply disposition`

Integraciones de navegación ligera:
- links hacia `/autonomy-campaigns`, `/autonomy-recovery`, `/autonomy-interventions`, `/approvals`, `/trace`, `/cockpit`
- quick link desde cockpit y desde autonomía recovery hacia `/autonomy-disposition`

Fuera de alcance: auto-close opaco, auto-abort opaco, dinero real, ejecución real broker/exchange, multiusuario complejo.


## Autonomy closeout board en `/autonomy-closeout` (new)

Nueva vista manual-first para cierre formal post-disposition:

- summary cards: candidates/ready/blocked/postmortem/memory/roadmap-feedback
- panel de reports con disposition, closeout status, final outcome y blockers
- findings estructurados (success/failure/blocker/incident/recovery/disposition lessons)
- recommendations explícitas (`COMPLETE_CLOSEOUT`, `SEND_TO_POSTMORTEM`, `INDEX_IN_MEMORY`, `PREPARE_ROADMAP_FEEDBACK`, `REQUIRE_MANUAL_CLOSEOUT_REVIEW`, `KEEP_OPEN_FOR_FOLLOWUP`)
- acción manual `Complete closeout` por campaña y `Run closeout review`
- quick links hacia `/autonomy-campaigns`, `/autonomy-disposition`, `/autonomy-recovery`, `/autonomy-interventions`, `/approvals`, `/trace`, `/cockpit`

## Autonomy followup UI in `/autonomy-followup` (new)

A new manual-first governance board now connects closeout outputs to formal handoff emission:

- summary cards for candidate/ready/blocked/emitted/duplicate counts
- candidates table with readiness, required followups, linked artifacts, blockers, and trace links
- followup history panel (`EMITTED`, `DUPLICATE_SKIPPED`, `BLOCKED`, etc.)
- recommendation panel (`EMIT_*`, `REQUIRE_MANUAL_REVIEW`, `SKIP_DUPLICATE_FOLLOWUP`)
- manual actions: `Run followup review` and `Emit followup`

Navigation is lightly integrated from `/autonomy-closeout` and `/cockpit` without redesigning existing pages.

## Autonomy feedback board en `/autonomy-feedback` (new)

Nueva vista para cerrar el knowledge loop posterior al handoff de `autonomy_followup`:

- summary cards: emitted, pending, in progress, completed, blocked y closed loop.
- tabla de candidates con `downstream_status`, artifact link, blockers y links a campaign/closeout/trace.
- panel de resolutions + recommendations para revisión manual-first.
- acción `Run feedback review` y `Complete resolution` (manual, auditado).

Integra `autonomy_followup`, `autonomy_closeout`, `approval_center`, `memory_retrieval`, `trace` y `cockpit` sin rediseñar arquitectura.

## Autonomy insights board in UI (new)

New route: `/autonomy-insights`

The board provides:
- lifecycle-closed candidate visibility
- summary cards for success/failure/blocker/governance patterns
- insights table with campaign/scope/type/target/confidence and trace links
- recommendations panel for governance actions (`REGISTER_MEMORY_PRECEDENT`, `PREPARE_ROADMAP_GOVERNANCE_NOTE`, `PREPARE_SCENARIO_CAUTION`, `PREPARE_PROGRAM_POLICY_NOTE`, `REQUIRE_OPERATOR_REVIEW`)
- manual `Run insights review` action and optional `Mark reviewed` action

Design constraints are preserved: manual-first, recommendation-first, no opaque auto-learning, no auto-policy/roadmap apply.


### Autonomy advisory resolution

The frontend includes `/autonomy-advisory-resolution` as a dedicated governance-note acknowledgment/adoption tracker:

- summary cards for emitted/pending/acknowledged/adopted/deferred/rejected
- candidate table with artifact/insight/campaign/target/blockers and trace links
- recommendation panel for explicit manual-first next actions
- manual actions: run review, acknowledge, adopt, defer, reject

The page is intentionally recommendation-first and audit-oriented, and does not auto-apply downstream changes.

## Autonomy backlog board en `/autonomy-backlog` (new)

Se agregó una vista formal de **future-cycle planning handoff** conectada a `autonomy_advisory_resolution`.

Qué muestra:
- summary cards: candidates, ready, blocked, created, prioritized, duplicate skipped
- tabla de candidates (artifact/insight/campaign/target/readiness/blockers)
- historial de backlog items con `backlog_type`, `backlog_status`, `priority_level`, `target_scope`
- panel de recomendaciones (`CREATE`, `PRIORITIZE`, `DEFER`, `SKIP_DUPLICATE`, `REQUIRE_MANUAL_BACKLOG_REVIEW`, `REORDER`)
- acciones manuales: run review, create backlog item, prioritize, defer

Integraciones UI:
- quick link desde `/autonomy-advisory-resolution` hacia `/autonomy-backlog`
- enlaces de trace desde backlog candidates a advisory / insight / campaign
- cockpit incorpora señal de atención cuando hay backlog crítico o pendientes de priorizar

Límites explícitos:
- no auto-apply opaco
- no mutaciones automáticas de roadmap/scenario/program/manager
- single-user, local-first, paper/sandbox only


## Autonomy intake board en `/autonomy-intake` (new)

Se agregó una ruta manual-first para convertir backlog formal en propuestas de planificación auditables.

Incluye:
- summary cards (candidates, ready, blocked, emitted, duplicate skipped, breakdown por target)
- tabla de intake candidates con links de trace a backlog/advisory/insight/campaign
- historial de `PlanningProposal` con estado (`PENDING_REVIEW`, `EMITTED`, `ACKNOWLEDGED`, etc.)
- panel de recomendaciones (`EMIT_*`, `SKIP_DUPLICATE_PROPOSAL`, `REQUIRE_MANUAL_INTAKE_REVIEW`, `REORDER_INTAKE_PRIORITY`)
- acciones manuales: `Run intake review`, `Emit proposal`, `Acknowledge`

Límites explícitos:
- no auto-apply opaco sobre roadmap/scenario/program/manager
- local-first, single-user, paper/sandbox only
