# Stabilization Batch 2 Completed (2026-04-22)

Referencias:
- Auditoría estructural base: `docs/architecture/stabilization-audit-2026-04-22.md`
- Batch 1: `docs/architecture/stabilization-batch-1-2026-04-22.md`

## Items del audit incluidos en Batch 2 (alcance conservador)

Este batch ejecuta únicamente ajustes medianos de lifecycle/contracts para Mission Control + Test Console + Cockpit, sin cambios de policy, launcher, LLM/training ni refactor masivo.

1. **Consolidación de lifecycle selector en frontend (Cockpit/Test Console)**
   - Se introdujo un selector reusable para separar de forma canónica:
     - `current active run`
     - `last completed run`
     - snapshot histórico efectivo
   - Se eliminó lógica heurística duplicada en `CockpitPage.tsx` para ese cálculo.

2. **Consumo consistente del lifecycle canónico en paneles frontend**
   - `DashboardPage.tsx` ahora reutiliza el mismo selector para distinguir `RUNNING` real vs estado terminal/idle al derivar frase ejecutiva.
   - Se reduce drift semántico entre Cockpit y paneles ejecutivos que consumen el mismo contrato.

3. **Eliminación de shaping redundante de status en Mission Control backend**
   - `TestConsoleStatusView` deja de re-aplicar `finalize_test_console_payload_for_serializer(...)` cuando el servicio ya entrega payload finalizado.
   - Se evita doble normalización/shaping del mismo payload en rutas de status.

4. **Documentación explícita de cierre Batch 2 y backlog pendiente**
   - Se deja registro formal de alcance, síntomas esperados y lo que se difiere a Batch 3/refactor mayor.

## Síntomas que deberían bajar con este batch

- Divergencia entre pantallas sobre qué significa “run activo” vs “última corrida completada”.
- Estados mezclados en Cockpit por heurísticas repetidas en más de un bloque/effect.
- Drift entre Dashboard y Cockpit sobre lifecycle real (`RUNNING` vs terminal/idle histórico).
- Riesgo de inconsistencias por doble shaping del mismo status payload en backend.

## Pospuesto explícitamente para Batch 3 / refactor mayor

### Batch 3 (todavía sin ejecutar)
- Política de polling central por dominio (intervalos/stop conditions/visibility) para Mission Control + Cockpit + Runtime.
- Paridad tipada end-to-end más estricta entre serializers backend y tipos frontend en toda la familia status/export/snapshot.
- Mayor reducción de defaults defensivos en payloads legacy de Test Console export.

### Refactor mayor (posterior)
- Rebanar `test_console.py` por módulos funcionales (lifecycle/snapshot/export/diagnostics).
- Modularización profunda de `mission_control/views.py` y serializers base compartidos.
- Limpieza estructural amplia de páginas frontend multipropósito (Cockpit/Mission Control/Runtime).
