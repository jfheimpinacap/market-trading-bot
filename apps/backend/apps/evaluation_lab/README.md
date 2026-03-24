# Evaluation Lab

`evaluation_lab` consolida métricas auditables para medir el desempeño del sistema autónomo paper/demo.

## Qué mide

- Volumen operacional: ciclos, propuestas, ejecuciones, pendientes y bloqueos.
- Calidad de reviews: favorable/neutral/unfavorable y tasas derivadas.
- Impacto de cartera: equity, PnL total/realizado/no realizado.
- Presión de safety: eventos, cooldown, hard-stop, kill-switch y errores.

## Endpoints

- `GET /api/evaluation/summary/`
- `GET /api/evaluation/runs/`
- `GET /api/evaluation/runs/<id>/`
- `POST /api/evaluation/build-for-session/<session_id>/`
- `GET /api/evaluation/recent/`
- `GET /api/evaluation/comparison/?left_id=<id>&right_id=<id>`

## Uso recomendado

1. Ejecutar sesiones en `/continuous-demo` y/o `/semi-auto`.
2. Construir evaluación por sesión con `build-for-session`.
3. Revisar `/evaluation` en frontend para snapshot técnico y runs recientes.

## Qué no hace (todavía)

- Optimización automática de estrategia/policy.
- ML o LLM.
- Ejecución real de dinero.
- Autoajuste autónomo.
