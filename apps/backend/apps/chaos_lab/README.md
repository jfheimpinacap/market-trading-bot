# chaos_lab

`chaos_lab` agrega una capa formal de **fault injection controlado** y **resilience benchmark** para el stack paper/demo.

## Alcance
- Inyección segura y reversible de fallos en módulos clave.
- Observación auditable de detección, mitigación, degraded mode y recuperación.
- Benchmark simple y transparente para comparar resiliencia entre configuraciones.

## No reemplaza
- No reemplaza `incident_commander`.
- No reemplaza `mission_control`.
- No reemplaza `rollout_manager`.

`chaos_lab` dispara escenarios y valida cómo los sistemas existentes responden.

## Fuera de alcance actual
- Dinero real.
- Ejecución real.
- Chaos distribuido enterprise.
- Orquestación de cluster.
