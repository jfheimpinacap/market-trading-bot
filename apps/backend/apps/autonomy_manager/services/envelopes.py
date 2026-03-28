from __future__ import annotations

from apps.autonomy_manager.models import AutonomyEnvelope


def build_envelope_payload(envelope: AutonomyEnvelope) -> dict:
    return {
        'max_auto_actions_per_cycle': envelope.max_auto_actions_per_cycle,
        'approval_override_behavior': envelope.approval_override_behavior,
        'blocked_contexts': envelope.blocked_contexts,
        'degraded_mode_handling': envelope.degraded_mode_handling,
        'certification_dependencies': envelope.certification_dependencies,
        'runtime_dependencies': envelope.runtime_dependencies,
        'metadata': envelope.metadata,
    }
