# learning_memory (demo, heuristic, auditable)

`learning_memory` agrega una capa local-first de memoria operativa para ajustar de forma conservadora (y explícita) proposal/risk.

## Qué sí hace
- Registra `LearningMemoryEntry` desde:
  - `TradeReview` (postmortem)
  - `EvaluationRun` / `EvaluationMetricSet`
  - eventos de `safety_guard`
- Construye `LearningAdjustment` activos por scope (`global`, `provider`, `source_type`, `signal_type`).
- Expone API para consultar memoria/ajustes/resumen y para reconstrucción (`rebuild`).
- Influye de manera acotada sobre:
  - `proposal_engine` (confidence + quantity + wording)
  - `risk_demo` (warning de cautela adicional)

## Qué NO hace
- No usa ML.
- No usa LLM.
- No ejecuta dinero real.
- No aplica optimización opaca.
- No reemplaza policy/risk; solo añade contexto heurístico conservador.

## Endpoints
- `GET /api/learning/memory/`
- `GET /api/learning/memory/<id>/`
- `GET /api/learning/adjustments/`
- `GET /api/learning/summary/`
- `POST /api/learning/rebuild/`

## Rebuild manual
```bash
cd apps/backend
python manage.py rebuild_learning_memory
```

## Diseño
- Determinístico y auditable (sin black-box).
- Ajustes con magnitudes pequeñas y acotadas.
- Persistencia explícita para trazabilidad en API y admin.


## Controlled learning loop integration (new)

Esta app ahora registra cada reconstrucción con `LearningRebuildRun` para trazabilidad operativa.

### Nuevos endpoints
- `GET /api/learning/rebuild-runs/`
- `GET /api/learning/rebuild-runs/<id>/`
- `GET /api/learning/integration-status/`

`POST /api/learning/rebuild/` se mantiene y ahora devuelve el `LearningRebuildRun` creado.

### Qué registra cada rebuild
- estado (`SUCCESS`, `PARTIAL`, `FAILED`)
- origen de disparo (`manual`, `automation`, `continuous_demo`, etc.)
- ventana procesada de memoria
- conteo de ajustes creados/actualizados/desactivados
- resumen + detalles auditables

### Integración conservadora
- `automation_demo` expone acciones manuales para rebuild y full learning cycle.
- `continuous_demo` puede activar rebuild automático de forma opcional y conservadora (desactivado por defecto).
- proposal/risk siguen usando ajustes heurísticos acotados; policy y safety mantienen prioridad.

### Fuera de alcance (se mantiene)
- ML real
- LLM local
- dinero real / ejecución real
- auto-optimización agresiva
