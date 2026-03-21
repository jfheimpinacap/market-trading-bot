# Frontend app

Frontend local-first para `market-trading-bot`, construido con React + Vite + TypeScript.

## Propósito en esta etapa

Esta aplicación ya no es solo un placeholder mínimo: ahora funciona como una base de plataforma con layout persistente, navegación entre módulos, páginas estructuradas y una integración simple con el backend local para consultar `GET /api/health/`.

El objetivo de esta fase es preparar una UI clara y mantenible para futuras iteraciones, sin introducir todavía autenticación, trading real, providers de mercado, machine learning ni estado global complejo.

## Estructura interna

```text
apps/frontend/src/
├── app/          # composición principal de la app y estado compartido de system health
├── components/   # bloques reutilizables de UI
├── hooks/        # hooks de frontend para datos y comportamiento
├── layouts/      # shell principal de la aplicación
├── lib/          # configuración y utilidades simples
├── pages/        # vistas por ruta
├── services/     # capa mínima de acceso a API
├── styles/       # estilos globales de la app
├── types/        # tipos TypeScript compartidos
└── store/        # reservado para estado compartido futuro
```

## Layout y navegación

La app usa un layout persistente tipo dashboard con:

- sidebar lateral con navegación principal
- topbar contextual según la sección activa
- área principal de contenido
- diseño responsive básico para notebook y escritorio

### Rutas actuales

- `/` — Dashboard
- `/markets` — Markets
- `/signals` — Signals
- `/agents` — Agents
- `/portfolio` — Portfolio
- `/postmortem` — Post-Mortem
- `/settings` — Settings
- `/system` — System
- fallback simple de página no encontrada

## Integración con backend local

La app consulta el healthcheck del backend mediante una capa liviana en `src/services/`.

Endpoint esperado:

```text
GET http://localhost:8000/api/health/
```

Variables mostradas en UI si el backend responde:

- backend online/offline
- `environment`
- `database_configured`
- `redis_configured`

Si la llamada falla, el dashboard y la página System muestran un estado offline claro sin romper la aplicación.

## Variable de entorno

Crea un archivo `.env` en `apps/frontend/` a partir del ejemplo:

```bash
cp .env.example .env
```

Contenido base:

```env
VITE_API_BASE_URL=http://localhost:8000
```

## Instalación

```bash
cd apps/frontend
npm install
```

## Ejecutar en local

```bash
cd apps/frontend
npm run dev
```

La app normalmente quedará disponible en la URL que imprima Vite, por ejemplo:

```text
http://localhost:5173
```

## Build de producción local

```bash
cd apps/frontend
npm run build
```

## Cómo verificar la conexión al backend

1. Levanta el backend en `http://localhost:8000`.
2. Asegúrate de que `VITE_API_BASE_URL` apunte a ese host.
3. Abre el dashboard `/`.
4. Revisa la tarjeta **Backend connection**.
5. Abre `/system` y usa el botón **Refresh health** si quieres relanzar la comprobación.

Si el backend está activo, deberías ver:

- estado online
- environment dev/local según backend
- indicadores de database y redis

Si el backend no está activo, verás un estado offline con mensaje de error claro.

## Qué es placeholder todavía

Las siguientes áreas siguen siendo placeholders serios, preparados para crecer en etapas futuras:

- Markets
- Signals
- Agents
- Portfolio
- Post-Mortem
- Settings
- System

Esto significa que ya tienen estructura, copy funcional y lugar dentro del shell, pero todavía no contienen lógica de negocio ni datos reales.

## Próximas etapas sugeridas

- añadir contratos de API para módulos reales
- conectar vistas de dominio gradualmente
- incorporar paneles técnicos adicionales para Redis, Celery y agentes
- modelar paper trading sin ejecutar trading real
- profundizar documentación de arquitectura frontend/backend
