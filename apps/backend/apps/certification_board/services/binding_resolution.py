from __future__ import annotations

from dataclasses import dataclass

from apps.certification_board.models import (
    ActivePaperBindingRecord,
    BaselineBindingResolutionStatus,
    CertificationDecision,
    PaperBaselineConfirmation,
)
from apps.champion_challenger.models import StackProfileBinding
from apps.policy_tuning.models import PolicyTuningCandidate
from apps.trust_calibration.models import TrustCalibrationRecommendation


@dataclass
class BindingResolutionResult:
    previous_baseline_reference: str
    proposed_baseline_reference: str
    binding_resolution_status: str
    blockers: list[str]
    snapshot: dict


@dataclass
class ActivationBindingResolutionResult:
    previous_active_reference: str
    proposed_active_reference: str
    activation_resolution_status: str
    blockers: list[str]
    snapshot: dict


def resolve_baseline_bindings(*, decision: CertificationDecision) -> BindingResolutionResult:
    blockers: list[str] = []
    certification_candidate = decision.linked_candidate
    promotion_case = certification_candidate.linked_promotion_case
    rollout_execution = certification_candidate.linked_rollout_execution

    champion = StackProfileBinding.objects.filter(is_champion=True, is_active=True).order_by('-updated_at', '-id').first()
    previous_reference = f'champion:{champion.id}:{champion.name}' if champion else ''
    if not previous_reference:
        blockers.append('missing_previous_champion_binding')

    proposed_reference = ''
    if promotion_case and promotion_case.proposed_value:
        proposed_reference = promotion_case.proposed_value
    elif rollout_execution and rollout_execution.summary:
        proposed_reference = f'rollout_execution:{rollout_execution.id}:{rollout_execution.summary}'
    elif decision.metadata.get('proposed_baseline_reference'):
        proposed_reference = str(decision.metadata['proposed_baseline_reference'])

    if not proposed_reference:
        blockers.append('missing_proposed_baseline_reference')

    latest_policy_candidate = PolicyTuningCandidate.objects.order_by('-created_at', '-id').first()
    latest_trust_recommendation = TrustCalibrationRecommendation.objects.order_by('-created_at', '-id').first()

    status = BaselineBindingResolutionStatus.RESOLVED
    if blockers:
        status = BaselineBindingResolutionStatus.BLOCKED
    elif not latest_policy_candidate or not latest_trust_recommendation:
        status = BaselineBindingResolutionStatus.PARTIAL

    if certification_candidate.target_scope == 'global' and status != BaselineBindingResolutionStatus.RESOLVED:
        blockers.append('global_scope_requires_resolved_bindings')
        status = BaselineBindingResolutionStatus.BLOCKED

    snapshot = {
        'champion_binding': {
            'id': champion.id if champion else None,
            'name': champion.name if champion else '',
            'execution_profile': champion.execution_profile if champion else '',
        },
        'policy_tuning_binding': {
            'candidate_id': latest_policy_candidate.id if latest_policy_candidate else None,
            'status': latest_policy_candidate.status if latest_policy_candidate else 'MISSING',
            'action_type': latest_policy_candidate.action_type if latest_policy_candidate else '',
        },
        'trust_calibration_binding': {
            'recommendation_id': latest_trust_recommendation.id if latest_trust_recommendation else None,
            'recommendation_type': latest_trust_recommendation.recommendation_type if latest_trust_recommendation else 'MISSING',
            'action_type': latest_trust_recommendation.action_type if latest_trust_recommendation else '',
        },
        'rollout_reference': {
            'rollout_execution_id': rollout_execution.id if rollout_execution else None,
            'promotion_case_id': promotion_case.id if promotion_case else None,
        },
    }

    return BindingResolutionResult(
        previous_baseline_reference=previous_reference,
        proposed_baseline_reference=proposed_reference,
        binding_resolution_status=status,
        blockers=blockers,
        snapshot=snapshot,
    )


def resolve_activation_bindings(*, confirmation: PaperBaselineConfirmation) -> ActivationBindingResolutionResult:
    blockers: list[str] = []
    previous_active = ActivePaperBindingRecord.objects.filter(
        target_component=confirmation.target_component,
        target_scope=confirmation.target_scope,
        status='ACTIVE',
    ).order_by('-updated_at', '-id').first()
    previous_reference = str((previous_active.active_snapshot or {}).get('reference') or '') if previous_active else ''

    proposed_reference = str((confirmation.confirmed_baseline_snapshot or {}).get('reference') or '')
    if not proposed_reference:
        blockers.append('missing_confirmed_baseline_reference')

    if previous_reference and proposed_reference and previous_reference == proposed_reference:
        blockers.append('equivalent_active_binding_already_set')

    binding_snapshot = confirmation.linked_candidate.metadata.get('binding_snapshot', {}) if confirmation.linked_candidate else {}

    status = BaselineBindingResolutionStatus.RESOLVED
    if blockers:
        status = BaselineBindingResolutionStatus.BLOCKED
    elif not binding_snapshot.get('policy_tuning_binding') or not binding_snapshot.get('trust_calibration_binding'):
        status = BaselineBindingResolutionStatus.PARTIAL

    return ActivationBindingResolutionResult(
        previous_active_reference=previous_reference,
        proposed_active_reference=proposed_reference,
        activation_resolution_status=status,
        blockers=blockers,
        snapshot={
            'current_active_binding': {
                'record_id': previous_active.id if previous_active else None,
                'binding_type': previous_active.active_binding_type if previous_active else '',
                'snapshot': previous_active.active_snapshot if previous_active else {},
            },
            'proposed_binding': confirmation.confirmed_baseline_snapshot,
            'baseline_confirmation': {
                'confirmation_id': confirmation.id,
                'candidate_id': confirmation.linked_candidate_id,
                'reason_codes': confirmation.reason_codes,
            },
            'policy_tuning_binding': binding_snapshot.get('policy_tuning_binding', {}),
            'trust_calibration_binding': binding_snapshot.get('trust_calibration_binding', {}),
            'champion_binding': binding_snapshot.get('champion_binding', {}),
            'rollout_reference': binding_snapshot.get('rollout_reference', {}),
        },
    )
