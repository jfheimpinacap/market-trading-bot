# Automation demo

`automation_demo` agrega una capa local-first de automatización guiada para acelerar la demo end-to-end sin introducir auto-trading, workers complejos ni agentes autónomos.

## Qué hace

- expone acciones explícitas para disparar pasos locales desde la UI o la API
- reutiliza la lógica ya existente de simulation, signals, paper trading y post-mortem
- registra cada ejecución en `DemoAutomationRun`
- soporta acciones individuales y un `run_demo_cycle` secuencial con trazabilidad por paso

## Acciones

- `simulate_tick`
- `generate_signals`
- `revalue_portfolio`
- `generate_trade_reviews`
- `sync_demo_state`
- `run_demo_cycle`

## Qué NO hace

- auto-trading
- scheduling real
- jobs en background persistentes
- colas distribuidas
- websockets
- integraciones reales con providers externos
- ejecución autónoma de agentes

## Endpoints

- `POST /api/automation/simulate-tick/`
- `POST /api/automation/generate-signals/`
- `POST /api/automation/revalue-portfolio/`
- `POST /api/automation/generate-trade-reviews/`
- `POST /api/automation/sync-demo-state/`
- `POST /api/automation/run-demo-cycle/`
- `GET /api/automation/runs/`
- `GET /api/automation/runs/<id>/`
- `GET /api/automation/summary/`

## Diseño

- las views son thin API boundaries
- la orquestación vive en `services.py`
- los resultados por paso se guardan en `details.steps`
- el demo cycle se detiene en el primer error y marca los pasos restantes como `SKIPPED`
