# Frontend app

Frontend local-first para `market-trading-bot`, construido con React + Vite + TypeScript.

## Qué muestra ahora el dashboard principal

La ruta `/` funciona como un centro de control local conectado al backend Django y muestra información real del sistema demo.

### Dashboard implementado en esta etapa

- header principal con estado general del entorno local
- bloque de estado del backend usando `GET /api/health/`
- bloque de contexto local con API base URL, runtime y modo actual
- resumen del catálogo de markets usando `GET /api/markets/system-summary/`
- accesos rápidos a módulos activos y placeholders del roadmap
- estado visual de módulos del proyecto con elementos listos vs pendientes
- sección liviana de markets recientes usando `GET /api/markets/`
- manejo robusto de loading, error y empty state por sección

## Qué hace ahora la página `/system`

La ruta `/system` ya no es un placeholder. Ahora funciona como un panel técnico para desarrollo local, pensado para verificar rápidamente el estado del backend, el contexto del entorno y señales observables de la simulación demo sin introducir nuevos endpoints ni control operativo desde la UI.

### Implementado en `/system`

- header técnico con badge de entorno local demo y refresh manual
- bloque **Backend health** reutilizando `useSystemHealth`
- bloque **Local runtime context** con API base URL, execution mode, data source y disponibilidad del simulation engine
- bloque **Market system overview** usando `GET /api/markets/system-summary/`
- bloque **Simulation activity view** usando `GET /api/markets/` para inferir actividad a partir de:
  - `latest_snapshot_at`
  - `snapshot_count`
  - cambios entre refreshes en `current_market_probability`, `liquidity`, `volume_24h`, `status` y timestamps
- bloque **Module readiness** con módulos ready vs pending
- bloque **Developer operations** con comandos útiles para operar localmente
- bloque **Quick links** hacia Dashboard, Markets y Settings
- manejo de loading, error parcial y empty state por sección

## Qué hace ahora el módulo Markets

El frontend incluye un módulo `Markets` funcional, conectado al backend Django local y orientado a inspeccionar datos demo reales sin introducir todavía trading, websockets ni integraciones externas.

### Implementado en esta etapa

- página `/markets` con header, summary cards y listado real de mercados
- filtros simples conectados al endpoint read-only del backend
- carga de providers y categorías para exploración local
- tabla desktop-first con navegación al detalle
- página `/markets/:marketId` con:
  - resumen principal del market
  - reglas (`short_rules` + `rules`)
  - snapshots recientes (`recent_snapshots`)
  - metadata útil para inspección
- estados claros de loading, error y empty state
- capa de servicios tipada en `src/services/markets.ts`
- tipos compartidos en `src/types/markets.ts`

## Estructura interna

```text
apps/frontend/src/
├── app/                # composición principal de la app y routing local
├── components/
│   ├── dashboard/      # UI reutilizable del dashboard principal
│   ├── markets/        # UI reutilizable del módulo Markets
│   ├── system/         # UI técnica específica para la página System
│   └── ...             # componentes compartidos del shell
├── hooks/              # hooks de frontend para datos y comportamiento
├── layouts/            # shell principal de la aplicación
├── lib/                # configuración y catálogos estáticos del frontend
├── pages/              # vistas por ruta
├── services/           # capa mínima de acceso a API
├── styles/             # estilos globales
├── types/              # tipos TypeScript compartidos
└── store/              # reservado para estado compartido futuro
```

## Rutas actuales

- `/` — Dashboard operativo local
- `/markets` — Markets explorer
- `/markets/:marketId` — Market detail
- `/signals` — Signals placeholder
- `/agents` — Agents placeholder
- `/portfolio` — Paper trading portfolio summary
- `/postmortem` — Post-Mortem placeholder
- `/settings` — Settings placeholder
- `/system` — System technical panel

## Endpoints consumidos por el frontend

### Dashboard principal

- `GET /api/health/`
- `GET /api/markets/system-summary/`
- `GET /api/markets/` (solo para una muestra liviana de markets recientes)

### System page

- `GET /api/health/`
- `GET /api/markets/system-summary/`
- `GET /api/markets/`

La página `/system` no agrega endpoints nuevos. Toda la evidencia de actividad se infiere comparando respuestas reales ya disponibles.

### Markets module

- `GET /api/markets/system-summary/`
- `GET /api/markets/providers/`
- `GET /api/markets/events/`
- `GET /api/markets/`
- `GET /api/markets/<id>/`

### Portfolio / paper trading

- `GET /api/paper/account/`
- `GET /api/paper/positions/`
- `GET /api/paper/trades/`
- `GET /api/paper/summary/`
- `POST /api/paper/revalue/`
- `GET /api/paper/snapshots/`

La ruta `/portfolio` ahora muestra:

- cuenta paper activa y contexto local demo
- summary cards para cash, equity, realized/unrealized/total PnL, open positions y total trades
- tabla de posiciones con side, quantity, avg entry, current mark, market value, PnL y estado
- historial de trades recientes ordenado por `executed_at`
- panel técnico de snapshots del portfolio
- acción manual **Revalue portfolio** que llama `POST /api/paper/revalue/` y luego refresca los datos visibles
- loading, error parcial, error total y empty states claros por sección

### Filtros usados en `/markets`

La UI envía estos parámetros al endpoint `GET /api/markets/` cuando corresponde:

- `provider`
- `category`
- `status`
- `is_active`
- `search`
- `ordering`

## Variable de entorno

Crea un archivo `.env` en `apps/frontend/` a partir del ejemplo:

```bash
cp .env.example .env
```

Contenido base:

```env
VITE_API_BASE_URL=http://localhost:8000
```

Si usas el launcher del repo, `python start.py setup` o `python start.py up` crea automáticamente `apps/frontend/.env` a partir de `apps/frontend/.env.example` cuando falta.

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

Qué resuelve el launcher para el frontend:

- valida que `apps/frontend/package.json` exista
- verifica que Node.js y npm estén disponibles
- resuelve `node`/`node.exe` y `npm`/`npm.cmd` explícitamente en Windows
- crea `apps/frontend/.env` si falta
- ejecuta `npm install` cuando `node_modules` no existe o cambian `package.json` / `package-lock.json`
- arranca Vite con host local y puerto `5173`
- en el flujo principal usa modo detached/single-console por defecto, sin abrir varias ventanas extra
- espera a que `http://localhost:5173/` responda antes de mostrar que el sistema está listo
- abre automáticamente `http://localhost:5173/system` salvo que uses `--no-browser`
- mantiene `--separate-windows` como opción de debug para volver al modo de ventanas separadas
- muestra accesos rápidos a `/`, `/system` y `/markets`

Atajos útiles:

```bash
python start.py
python start.py --no-browser
python start.py --separate-windows
python start.py frontend
python start.py frontend --no-browser
```

## Cómo levantar backend + seed demo + simulación + frontend

### Opción recomendada: un solo comando

```bash
python start.py
```

Para apagar backend + frontend + infraestructura local:

```bash
python start.py down
```

### 1. Backend Django

```bash
cd apps/backend
python manage.py migrate
python manage.py seed_markets_demo
python manage.py seed_paper_account
python manage.py runserver
```

El backend local quedará disponible normalmente en:

```text
http://localhost:8000
```

### 2. Simulación local

Para generar movimiento observable en `/system`, ejecuta uno de estos comandos en otra terminal:

```bash
cd apps/backend
python manage.py simulate_markets_tick
```

O bien:

```bash
cd apps/backend
python manage.py simulate_markets_loop
```

### 3. Frontend

```bash
cd apps/frontend
npm install
cp .env.example .env
npm run dev
```

La app normalmente quedará disponible en la URL que imprima Vite, por ejemplo:

```text
http://localhost:5173
```

## Cómo verificar visualmente que `/system` funciona

1. Abre `http://localhost:5173/system`.
2. Confirma que **Backend health** refleje el estado real de `GET /api/health/`.
3. Revisa que **Local runtime context** muestre la `VITE_API_BASE_URL` esperada y el modo `Local demo`.
4. Verifica que **Market system overview** muestre providers, events, markets, active/resolved y snapshots.
5. Mira **Simulation activity view** y confirma que exista una lista de markets recientes con `snapshot_count`, `latest_snapshot_at`, probabilidad, liquidez y volumen.
6. Ejecuta `python manage.py simulate_markets_tick`.
7. Pulsa **Refresh system data**.
8. Verifica que cambie al menos una de estas señales:
   - **Snapshot delta since refresh**
   - **Changed market rows**
   - timestamps recientes en **Latest observed snapshot**
   - métricas de markets como probability, liquidity o volume 24h

## Cómo verificar que el dashboard y Markets siguen funcionando

1. Abre `http://localhost:5173/`.
2. Confirma que el bloque **Backend API** refleja el estado real de `GET /api/health/`.
3. Verifica que **Market system overview** muestre providers, events, markets y snapshots.
4. Revisa que **Recent markets** liste contratos reales y permita navegar a `/markets/:marketId`.
5. Abre `http://localhost:5173/markets` y valida filtros, tabla y navegación al detalle.
6. Si apagas el backend, confirma que la UI no rompe y muestra los estados de error/offline por sección.

## Build de producción local

```bash
cd apps/frontend
npm run build
```

## Qué quedó preparado para la siguiente etapa

La implementación deja lista una base útil para evolucionar sin reescribir el frontend:

- `/system` ya consume salud, resumen del catálogo y actividad observable usando solo APIs existentes
- la comparación entre refreshes deja preparada una base sencilla para futuras señales o auto-refresh liviano
- la estructura `components/system/` permite ampliar la vista técnica sin volver la página monolítica
- la página sigue reutilizando `useSystemHealth`, `services/markets.ts`, `services/api/client.ts` y `DataStateWrapper`
- la UI técnica ya separa claramente lo disponible hoy de lo que sigue pendiente

## Qué partes siguen siendo placeholder

Todavía siguen como placeholder o reservadas para roadmap:

- Signals
- Agents
- Post-Mortem
- Settings avanzados
- sincronización real con providers
- señales operativas avanzadas y risk engine

## Qué sigue después

Siguientes pasos razonables después de esta iteración:

- añadir auto-refresh opcional muy ligero si realmente aporta durante desarrollo local
- exponer más diagnósticos del backend cuando existan endpoints específicos
- conectar resúmenes reales para Agents cuando existan endpoints
- evolucionar `/portfolio` desde visibilidad read-only hacia ejecución controlada de paper trades cuando esa UX entre en alcance
- preparar una capa de señales o telemetry local sin caer aún en observabilidad compleja

## Qué NO se implementó todavía

Sigue fuera de alcance en esta etapa:

- trading real
- paper trading operativo
- start/stop del simulation loop desde la UI
- websockets
- streaming en tiempo real
- charts avanzados
- autenticación
- machine learning
- integración real con providers
- paneles complejos de observabilidad
- consola o terminal embebida
- logs persistentes
- estado global sofisticado
- risk engine
- signals engine operativo

## Notas de desarrollo

- La capa de datos se mantiene simple con `fetch`, sin React Query.
- El dashboard y `/system` reutilizan `useSystemHealth`, `services/health.ts`, `services/markets.ts` y `DataStateWrapper`.
- La evidencia de simulación en `/system` es deliberadamente inferida; no pretende inventar precisión que el backend aún no expone directamente.
- El diseño sigue siendo sobrio, desktop-first y orientado a entorno local.
- Si el backend no está activo, la UI muestra errores claros y no rompe la navegación general.

## Cómo probar `/portfolio`

1. Asegúrate de que el backend esté corriendo en `http://localhost:8000` y que `apps/frontend/.env` tenga `VITE_API_BASE_URL=http://localhost:8000`.
2. Inicializa la cuenta demo con:

```bash
cd apps/backend
python manage.py seed_paper_account
```

3. Si quieres actividad visible, registra trades demo desde backend o script y luego entra a `http://localhost:5173/portfolio`.
4. Verifica que las secciones **Account metrics**, **Positions**, **Trades** y **Snapshots** carguen desde los endpoints paper existentes.
5. Pulsa **Revalue portfolio** para disparar `POST /api/paper/revalue/`.
6. Confirma que cambian `updated_at`, snapshots y los valores de equity / unrealized PnL cuando el backend recalcula el portfolio.

## Qué falta todavía para paper trading completo

Esta etapa sigue siendo solo de visualización. Aún no se implementa en frontend:

- ejecución de compras/ventas desde la UI
- formularios de trading o tickets de orden
- websockets o auto-refresh continuo
- charts avanzados de equity o PnL
- trading real, autenticación, multiusuario o risk engine
