# Stabilization Audit (2026-04-22)

## Alcance y método

Auditoría **estructural** (sin refactor masivo y sin cambios de policy) enfocada en:

- Backend + frontend de Mission Control / Test Console / Cockpit / Runtime Advanced.
- Contratos `status/export/snapshot`.
- Polling y sincronización UI/estado.
- Superposición de responsabilidades y señales de código legacy.

Evidencia usada:

- Tamaño de archivos críticos (`wc -l`).
- Puntos de polling/refresh y side effects (`rg useEffect|setInterval|URLSearchParams`).
- Superficie de endpoints y contratos (`mission_control/urls.py`, `serializers.py`, `views.py`, servicios frontend).
- Fragilidad histórica orientativa por frecuencia de cambios (`git log --name-only | uniq -c`).

---

## Métricas orientativas (fragilidad/acoplamiento)

- El repo tiene al menos **256,734 líneas** en archivos de código/docs principales (sin `node_modules`).
- Hot files por tamaño (señal de acoplamiento):
  - `live_paper_autonomy_funnel.py` (6108 líneas)
  - `test_console.py` (2427)
  - `mission_control/views.py` (1226)
  - `MissionControlPage.tsx` (611)
  - `RuntimePage.tsx` (1244)
- Hot files por churn histórico (aprox. por commits):
  - `apps/backend/apps/mission_control/tests.py` (99)
  - `apps/frontend/src/pages/CockpitPage.tsx` (86)
  - `apps/backend/apps/mission_control/serializers.py` (58)
  - `apps/backend/apps/mission_control/services/test_console.py` (54)
  - `apps/backend/apps/mission_control/services/live_paper_autonomy_funnel.py` (52)

Lectura: el problema dominante no es una sola función defectuosa, sino **superficie enorme + contratos distribuidos + churn continuo en los mismos módulos**.

---

## Top 10 hotspots técnicos

## 1) `test_console.py` como módulo monolítico multi-responsabilidad
- **Severidad:** Alta
- **Síntoma:** bugs repetitivos en status/export, regressions por cambios “inocentes”, difícil trazabilidad.
- **Módulos:** `apps/backend/apps/mission_control/services/test_console.py`
- **Por qué conflictivo:** mezcla ciclo de ejecución, ensamblado de payload, logging textual, snapshots operativos, normalización y fallback en un solo archivo de 2.4k líneas.
- **Recomendación:** separar por capas (run lifecycle / status snapshot / export shaping / diagnostics adapters) con contratos internos explícitos.

## 2) Contratos opcionales inconsistentes (`NO_RUN_YET` vs `404` vs null)
- **Severidad:** Alta
- **Síntoma:** manejo defensivo duplicado en frontend, estados ambiguos (vacío vs error), UI stale o intermitente.
- **Módulos:** `mission_control/views.py`, `mission_control/serializers.py`, `frontend/services/missionControl.ts`
- **Por qué conflictivo:** coexistencia de patrón legacy `404` con patrón nuevo `200 + exists/status`, obligando wrappers especiales (`requestOptionalStatusJson`) y normalización ad-hoc.
- **Recomendación:** contrato único `OptionalRunStatus<T>` para todos los endpoints opcionales; deprecar rutas/comportamientos legacy por fases.

## 3) Multiplicidad de rutas API equivalentes (slash / no-slash)
- **Severidad:** Media-Alta
- **Síntoma:** clientes con variantes de path, dificultad de observabilidad, pruebas más frágiles.
- **Módulos:** `apps/backend/apps/mission_control/urls.py`
- **Por qué conflictivo:** varios endpoints duplicados para misma vista (`run-live-paper-trial`, `.../`, `status`, etc.).
- **Recomendación:** consolidar en una convención única y mantener compatibilidad mediante redirect/deprecation window.

## 4) `MissionControlPage.tsx` con carga fan-out masiva en un solo `Promise.all`
- **Severidad:** Alta
- **Síntoma:** fallos parciales tumban carga global, difícil aislar error por dominio, re-render y estado excesivo.
- **Módulos:** `apps/frontend/src/pages/mission-control/MissionControlPage.tsx`
- **Por qué conflictivo:** una sola rutina `load()` orquesta decenas de fetches y sets de estado independientes.
- **Recomendación:** particionar por dominios (timing/health/recovery/governance) con boundaries de error separados.

## 5) `CockpitPage.tsx` como agregado de múltiples fuentes de verdad
- **Severidad:** Alta
- **Síntoma:** UI stale, snapshots inconsistentes, badges con estados distintos para el mismo proceso.
- **Módulos:** `apps/frontend/src/pages/CockpitPage.tsx`
- **Por qué conflictivo:** combina `testConsoleStatus`, `lastCompletedTestConsoleSnapshot`, snapshots de trial/status/result y múltiples defaults/fallbacks.
- **Recomendación:** introducir un selector/adapter único de “estado efectivo” por dominio con precedencia formal documentada.

## 6) Polling acotado pero no centralizado por dominio
- **Severidad:** Media
- **Síntoma:** refresh desigual entre pantallas; una parte poll-ea (`test-console`) y otras dependen de recarga manual.
- **Módulos:** `apps/frontend/src/hooks/usePollingTicker.ts`, `apps/frontend/src/pages/CockpitPage.tsx`, `MissionControlPage.tsx`
- **Por qué conflictivo:** no existe “polling policy” compartida (intervalos, stop conditions, visibility handling, backoff).
- **Recomendación:** estandarizar una política de polling por tipo de recurso (run-active, read-only summary, historical lists).

## 7) Shaping duplicado de query params y llamadas API
- **Severidad:** Media
- **Síntoma:** errores por divergencia sutil en parámetros/filtros, costo de mantenimiento alto.
- **Módulos:** `apps/frontend/src/services/missionControl.ts`, `apps/frontend/src/services/runtime.ts`
- **Por qué conflictivo:** repetición de patrones `URLSearchParams` y construcción manual de query strings en muchos métodos.
- **Recomendación:** helper genérico `buildQuery` + contratos typed por endpoint.

## 8) Serializers extensos con familias de contratos solapados
- **Severidad:** Media-Alta
- **Síntoma:** drift semántico entre `Result`/`Status`/`Summary`, campos opcionales crecientes y defaults implícitos.
- **Módulos:** `apps/backend/apps/mission_control/serializers.py`, `apps/frontend/src/types/missionControl.ts`
- **Por qué conflictivo:** varios serializers comparten estructura parcial (`exists/status/summary/reason_code`) sin base común.
- **Recomendación:** factorizar esquemas base de estado opcional + versionado ligero para payloads críticos.

## 9) Defaults defensivos extensivos que ocultan datos faltantes reales
- **Severidad:** Alta
- **Síntoma:** bugs silenciosos (“todo parece OK pero con UNKNOWN/n/a/0”).
- **Módulos:** `test_console.py`, `CockpitPage.tsx`, `missionControl.ts`
- **Por qué conflictivo:** uso intensivo de `or`, `??`, valores centinela y coerciones que enmascaran rupturas de contrato.
- **Recomendación:** diferenciar explícitamente `missing_data` vs `negative_result` y elevar warnings estructurados.

## 10) Hotspots históricos concentrados en Mission Control/Cockpit/tests
- **Severidad:** Media-Alta
- **Síntoma:** alta tasa de fixes re-activos en los mismos archivos.
- **Módulos:** `mission_control/tests.py`, `CockpitPage.tsx`, `mission_control/serializers.py`, `test_console.py`
- **Por qué conflictivo:** el churn repetitivo en módulos grandes aumenta probabilidad de regresión cruzada.
- **Recomendación:** congelar superficie, definir ownership por dominio y exigir contract tests antes de nuevos fixes puntuales.

---

## Quick wins seguros vs fixes medianos vs refactors grandes

### Quick wins seguros (1-2 sprints)
1. Definir contrato único de estado opcional (`exists`, `status`, `reason_code`, `next_action_hint`) para smoke/trial/extended status.
2. Normalizar rutas API (slash canonical) manteniendo compatibilidad temporal.
3. Crear helper frontend de query params para eliminar duplicación de `URLSearchParams`.
4. Añadir banderas de `data_freshness`/`missing_sections` en payloads Test Console export/status (sin tocar policy).
5. Añadir tests de contrato snapshot/status/export para NO_RUN_YET vs run activo/completado.

### Fixes medianos (2-4 sprints)
1. Dividir `MissionControlPage` en loaders por dominio con error boundaries por bloque.
2. Consolidar “effective snapshot selection” en Cockpit/Test Console en un único selector reusable.
3. Introducir una `PollingPolicy` central (intervalos + stop conditions + visibility).
4. Reconciliar tipos frontend `missionControl.ts` con serializers backend en un checklist de paridad.

### Refactors grandes (postergar, planificados)
1. Rebanar `test_console.py` en módulos funcionales (run lifecycle / snapshot sync / export composer / diagnostics).
2. Rebanar `live_paper_autonomy_funnel.py` por etapas y contratos de stage.
3. Modularizar `views.py` en sub-routers por dominio (runtime/timing/health/recovery/governance/live-paper).

---

## Código potencialmente eliminable/consolidable/unificable

### Eliminable (tras ventana de deprecación)
- Endpoints duplicados slash/no-slash en Mission Control.
- Fallback 404 legacy para estados opcionales cuando ya existe `NO_RUN_YET` consistente.

### Consolidable
- Construcción de query strings en servicios frontend.
- Lógica de selección de snapshot “actual vs último completado” en Cockpit/Test Console.
- Helpers de respuesta de estado opcional en backend (factory común).

### Contratos a unificar
- `LivePaperSmokeTestStatus`, `LivePaperTrialRunStatus`, `ExtendedPaperRunStatus`.
- Bloques comunes de summary/reason codes/next action en status/export.
- Semántica de `UNKNOWN`, `n/a`, `null`, `exists=false`.

---

## Plan de estabilización en 3 fases

## Fase 1 — lifecycle/contracts (prioridad máxima)
- Congelar contratos críticos (`status/export/snapshot`) y documentar matriz de estados.
- Implementar contrato base de estado opcional.
- Agregar pruebas de contrato backend + frontend adapters.
- Definir y comunicar deprecaciones (slash/no-slash, 404 legacy).

## Fase 2 — polling/state/UI sync
- Introducir política central de polling.
- Separar carga por dominio en Mission Control/Cockpit.
- Reducir múltiples fuentes de verdad de cada panel a un selector único de estado efectivo.
- Agregar indicador explícito de frescura/edad de datos por bloque.

## Fase 3 — consolidación/cleanup
- Extraer módulos de `test_console.py` y `live_paper_autonomy_funnel.py` en capas.
- Consolidar serializers base y normalizadores.
- Retirar rutas y contratos legacy deprecados.
- Cerrar con suite de regresión de snapshots/status/export.

---

## Resumen ejecutivo (Codex)

1. **Mayores focos de fragilidad:** archivos monolíticos de Mission Control/Test Console + páginas frontend multipropósito con demasiadas responsabilidades y estado disperso.
2. **Qué causa bugs repetitivos:** contratos parcialmente inconsistentes (especialmente estados opcionales), defaults defensivos que silencian drift, y churn alto en los mismos hotspots.
3. **Orden correcto de limpieza:** primero contratos/lifecycle (Fase 1), luego sincronización polling/estado/UI (Fase 2), y por último consolidación estructural profunda (Fase 3).
