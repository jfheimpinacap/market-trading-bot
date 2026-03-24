# Safety Guard (paper/demo only)

This app adds operational hardening guardrails above risk/policy.

## Scope
- Conservative limits for exposure, drawdown, auto trades, and error streaks.
- Cooldown (soft stop), hard stop, and explicit kill switch.
- Auditable `SafetyEvent` records for every relevant trigger.

## Core models
- `SafetyPolicyConfig`: persisted limits + mutable safety state.
- `SafetyEvent`: immutable audit events for warnings/stops/escalations.

## API
- `GET /api/safety/status/`
- `GET /api/safety/events/`
- `GET /api/safety/events/<id>/`
- `POST /api/safety/kill-switch/enable/`
- `POST /api/safety/kill-switch/disable/`
- `GET/POST /api/safety/config/`
- `POST /api/safety/reset-cooldown/`
- `GET /api/safety/summary/`

## Integration
- `continuous_demo` checks safety status before each cycle and after each cycle.
- `semi_auto_demo` evaluates safety before auto execution and can escalate AUTO_APPROVE to pending manual approval.
- Kill switch blocks new auto execution and continuous loop start.
