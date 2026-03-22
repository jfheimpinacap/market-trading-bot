# Frontend app

Frontend local-first para `market-trading-bot`, construido con React + Vite + TypeScript.

## Qué hace ahora el módulo Markets

El frontend ya incluye un módulo `Markets` funcional, conectado al backend Django local y orientado a inspeccionar datos demo reales sin introducir todavía trading, websockets ni integraciones externas.

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
│   ├── markets/        # UI reutilizable del módulo Markets
│   └── ...             # componentes compartidos del shell
├── hooks/              # hooks de frontend para datos y comportamiento
├── layouts/            # shell principal de la aplicación
├── lib/                # configuración y utilidades simples
├── pages/
│   ├── markets/        # páginas reales de Markets
│   └── ...             # resto de páginas del shell
├── services/           # capa mínima de acceso a API
├── styles/             # estilos globales
├── types/              # tipos TypeScript compartidos
└── store/              # reservado para estado compartido futuro
```

## Rutas actuales

- `/` — Dashboard
- `/markets` — Markets explorer
- `/markets/:marketId` — Market detail
- `/signals` — Signals placeholder
- `/agents` — Agents placeholder
- `/portfolio` — Portfolio placeholder
- `/postmortem` — Post-Mortem placeholder
- `/settings` — Settings placeholder
- `/system` — System technical panel

## Endpoints consumidos por el frontend

### Health general ya existente

- `GET /api/health/`

### Markets module

- `GET /api/markets/system-summary/`
- `GET /api/markets/providers/`
- `GET /api/markets/events/`
- `GET /api/markets/`
- `GET /api/markets/<id>/`

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

## Cómo levantar backend + seed demo + frontend

### 1. Backend Django

```bash
cd apps/backend
python manage.py migrate
python manage.py seed_markets_demo
python manage.py runserver
```

El backend local quedará disponible normalmente en:

```text
http://localhost:8000
```

### 2. Frontend

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

## Cómo navegar y probar el módulo Markets

1. Abre `http://localhost:5173/markets`.
2. Revisa las tarjetas de resumen superior.
3. Usa filtros por provider, category, status, active o search.
4. Haz click sobre cualquier fila de la tabla.
5. El frontend navegará a `http://localhost:5173/markets/<marketId>`.
6. Desde el detalle puedes volver con **Back to markets**.

## Build de producción local

```bash
cd apps/frontend
npm run build
```

## Qué quedó preparado para la siguiente etapa

La implementación ya deja lista una base útil para evolucionar sin reescribir el módulo:

- servicios de API reutilizables y tipados
- separación entre páginas, componentes y tipos
- navegación entre listado y detalle
- presentación consistente para estados y badges
- soporte inicial para ordering desde la UI
- base visual compatible con futuras mejoras como paginación simple, watchlists o comparativas

## Qué NO se implementó todavía

Sigue fuera de alcance en esta etapa:

- trading real
- paper trading operativo
- charts avanzados
- websockets
- autenticación
- machine learning
- integración real con providers
- dashboards complejos
- CRUD de markets
- estado global sofisticado
- cache avanzada
- comparación de mercados
- watchlists
- tiempo real

## Notas de desarrollo

- La capa de datos se mantiene simple con `fetch`, sin React Query.
- El diseño es deliberadamente sobrio y desktop-first.
- Si el backend no está activo, la UI muestra errores claros y no rompe la navegación general.
