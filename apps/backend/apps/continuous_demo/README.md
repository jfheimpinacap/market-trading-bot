# Continuous Demo Loop

`continuous_demo` agrega un loop autónomo y conservador para ejecutar ciclos continuos en **paper/demo only**.

## Qué hace

Cada ciclo reutiliza servicios existentes:

1. `automation_demo.run_demo_cycle` (refresh/ingesta demo, señales, revalue, reviews)
2. `semi_auto_demo.run_scan_and_execute` (propuestas + policy/risk + autoejecución paper segura)
3. post-procesado opcional (revalue/reviews tras auto trades)

## Controles

- `POST /api/continuous-demo/start/`
- `POST /api/continuous-demo/pause/`
- `POST /api/continuous-demo/resume/`
- `POST /api/continuous-demo/stop/` (`kill_switch` opcional)
- `POST /api/continuous-demo/run-cycle/`

## Seguridad

- Nunca ejecuta trading real.
- Sólo opera en `paper_trading`.
- `APPROVAL_REQUIRED` crea `PendingApproval` en `semi_auto_demo`.
- `HARD_BLOCK` jamás se ejecuta.
- Una sola sesión `RUNNING` a la vez.
- `kill_switch` detiene e impide nuevos ciclos hasta desactivarlo.
