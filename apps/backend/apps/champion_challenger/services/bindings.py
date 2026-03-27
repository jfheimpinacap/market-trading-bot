from __future__ import annotations

from apps.execution_simulator.models import ExecutionPolicyProfile
from apps.prediction_training.services.registry import get_active_model_artifact
from apps.profile_manager.services.profiles import ensure_default_bindings, resolve_profile
from apps.profile_manager.services.state import build_profile_state_snapshot

from apps.champion_challenger.models import StackProfileBinding


def _current_runtime_constraints() -> dict:
    return build_profile_state_snapshot()


def _default_binding_payload() -> dict:
    ensure_default_bindings()
    runtime = _current_runtime_constraints()
    operating_mode = runtime.get('runtime_mode', 'balanced').lower()
    if operating_mode not in {'conservative', 'balanced', 'aggressive_light'}:
        operating_mode = 'balanced'
    return {
        'prediction_model_artifact': get_active_model_artifact(),
        'prediction_profile_slug': operating_mode,
        'research_profile_slug': resolve_profile('research_agent', operating_mode),
        'signal_profile_slug': resolve_profile('signals', operating_mode),
        'opportunity_supervisor_profile_slug': resolve_profile('opportunity_supervisor', operating_mode),
        'mission_control_profile_slug': resolve_profile('mission_control', operating_mode),
        'portfolio_governor_profile_slug': resolve_profile('portfolio_governor', operating_mode),
        'execution_profile': ExecutionPolicyProfile.BALANCED,
        'runtime_constraints_snapshot': runtime,
    }


def get_or_create_champion_binding() -> StackProfileBinding:
    champion = StackProfileBinding.objects.filter(is_champion=True, is_active=True).order_by('-updated_at', '-id').first()
    if champion:
        return champion

    payload = _default_binding_payload()
    return StackProfileBinding.objects.create(name='active_champion', is_champion=True, is_active=True, **payload)


def create_challenger_binding(*, name: str, overrides: dict | None = None) -> StackProfileBinding:
    payload = _default_binding_payload()
    overrides = overrides or {}
    if overrides.get('prediction_model_artifact_id'):
        from apps.prediction_training.models import PredictionModelArtifact

        payload['prediction_model_artifact'] = PredictionModelArtifact.objects.filter(id=overrides['prediction_model_artifact_id']).first()

    for key in [
        'prediction_profile_slug',
        'research_profile_slug',
        'signal_profile_slug',
        'opportunity_supervisor_profile_slug',
        'mission_control_profile_slug',
        'portfolio_governor_profile_slug',
        'execution_profile',
        'runtime_constraints_snapshot',
    ]:
        if key in overrides and overrides[key] is not None:
            payload[key] = overrides[key]

    return StackProfileBinding.objects.create(name=name, is_champion=False, is_active=False, **payload)


def set_champion_binding(*, binding: StackProfileBinding) -> StackProfileBinding:
    StackProfileBinding.objects.filter(is_champion=True).update(is_champion=False)
    binding.is_champion = True
    binding.is_active = True
    binding.save(update_fields=['is_champion', 'is_active', 'updated_at'])
    return binding
