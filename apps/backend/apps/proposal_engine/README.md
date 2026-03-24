# Proposal Engine (demo, backend-only)

`apps.proposal_engine` construye propuestas operativas demo (`TradeProposal`) para un market, unificando contexto de:

- `markets` (estado y precios actuales + snapshots recientes)
- `signals` (señales recientes, dirección y accionabilidad)
- `risk_demo` (trade guard)
- `policy_engine` (approval rules)
- `paper_trading` (cash y exposición del paper account)

Todo el flujo es **local-first** y **demo-only**.

## Objetivo

Producir una propuesta legible y auditable, separada de la ejecución:

- `direction`: `BUY_YES` / `BUY_NO` / `HOLD` / `AVOID`
- `thesis` y `rationale`
- `suggested_trade_type`, `suggested_side`, `suggested_quantity`
- `risk_decision`, `policy_decision`
- `approval_required`, `is_actionable`, `recommendation`

## Modelo principal

`TradeProposal` persiste:

- identidad y relación a `market` + `paper_account` (opcional)
- estado de propuesta (`ACTIVE`, `STALE`, etc.)
- contenido operativo sugerido (tipo, lado, cantidad, referencia de precio)
- decisiones de riesgo y policy
- trazabilidad (`metadata`, timestamps, `expires_at`)

## Servicios

- `services/context.py`: arma el contexto consolidado del market/account/señales.
- `services/heuristics.py`: aplica reglas demo explicables y determina dirección, sizing, risk y policy.
- `services/proposal.py`: orquesta y persiste `TradeProposal`.

## Heurísticas demo implementadas

1. **Dirección por señales**
   - Señales accionables y sesgo bullish -> `BUY_YES`
   - Señales accionables y sesgo bearish -> `BUY_NO`
   - Señales mixtas -> `HOLD`
   - Sin edge claro -> `AVOID`

2. **Sizing simple**
   - Budget base pequeño (fracción de cash)
   - Ajuste por confidence
   - Reducción si ya existe exposición relevante en ese market
   - Ajuste adicional si `risk_demo` devuelve `CAUTION`

3. **Guardrails operativos**
   - Se ejecuta `risk_demo.assess_trade`
   - Se ejecuta `policy_engine.evaluate_trade_policy`
   - Si `HARD_BLOCK`, propuesta no actionable

## Endpoints

- `GET /api/proposals/`
- `GET /api/proposals/<id>/`
- `POST /api/proposals/generate/`

Payload mínimo para generar:

```json
{
  "market_id": 1,
  "paper_account_id": 1,
  "triggered_from": "market_detail"
}
```

## Fuera de alcance (intencional)

- frontend de proposals
- auto-trading / auto-ejecución
- datos reales
- ML / LLM / agentes autónomos
- approval queue compleja
- websockets
