# Frontend app

Frontend local-first para `market-trading-bot`, construido con React + Vite + TypeScript.

## Qué quedó refinado en esta etapa

El frontend ya no se siente como un conjunto de módulos separados. La UX ahora enfatiza un recorrido demo coherente:

1. **Dashboard** para entender el estado general del sistema demo.
2. **Markets** para descubrir contratos activos.
3. **Signals** para detectar oportunidades demo y saltar al market correcto.
4. **Market detail** para revisar señal, evaluar riesgo y ejecutar paper trade.
5. **Portfolio** para ver impacto en equity, posiciones y trades.
6. **Post-mortem** para revisar outcome, lecciones y volver al market o portfolio.

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
- workflow summary visible con:
  - señales del market
  - última decisión de riesgo conocida
  - estado de posición abierta
  - latest review si existe
- CTA claros hacia `Portfolio`, `Signals` y `Post-Mortem`
- después de ejecutar un trade, la página refresca contexto de trading y publica un refresh liviano para el resto del flujo

### `/portfolio`
- posiciones con link claro a market detail
- trades con link claro a review cuando existe
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
- `POST /api/paper/trades/`
- `GET /api/paper/account/`
- `GET /api/paper/positions/`
- `GET /api/paper/trades/`
- `GET /api/paper/summary/`
- `POST /api/paper/revalue/`

### Signals
- `GET /api/signals/summary/`
- `GET /api/signals/agents/`
- `GET /api/signals/`
- `GET /api/paper/positions/`
- `GET /api/paper/trades/`
- `GET /api/reviews/`

### Portfolio
- `GET /api/paper/account/`
- `GET /api/paper/positions/`
- `GET /api/paper/trades/`
- `GET /api/paper/summary/`
- `POST /api/paper/revalue/`
- `GET /api/paper/snapshots/`
- `GET /api/reviews/`

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
- `/markets/:marketId` — Market detail + risk + paper trade
- `/signals` — Demo signals workspace
- `/agents` — Agents placeholder
- `/portfolio` — Paper trading portfolio summary
- `/postmortem` — Post-mortem trade review queue
- `/postmortem/:reviewId` — Post-mortem review detail
- `/settings` — Settings placeholder
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
python start.py setup
python start.py frontend
python start.py status
python start.py down
```
