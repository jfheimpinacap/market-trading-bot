from __future__ import annotations

from django.utils import timezone

from apps.certification_board.models import (
    BaselineBindingSnapshot,
    BaselineBindingStatus,
    BaselineBindingType,
    BaselineConfirmationCandidate,
    PaperBaselineConfirmation,
    PaperBaselineConfirmationStatus,
)


def get_or_create_confirmation(*, candidate: BaselineConfirmationCandidate) -> PaperBaselineConfirmation:
    status = (
        PaperBaselineConfirmationStatus.READY_TO_CONFIRM
        if candidate.ready_for_confirmation
        else PaperBaselineConfirmationStatus.BLOCKED
    )
    confirmation, _ = PaperBaselineConfirmation.objects.get_or_create(
        linked_candidate=candidate,
        defaults={
            'linked_certification_decision': candidate.linked_certification_decision,
            'confirmation_status': status,
            'target_component': candidate.target_component,
            'target_scope': candidate.target_scope,
            'previous_baseline_snapshot': {
                'reference': candidate.previous_baseline_reference,
            },
            'confirmed_baseline_snapshot': {
                'reference': candidate.proposed_baseline_reference,
            },
            'rationale': (
                'Baseline candidate has resolved mappings and is ready for manual confirmation.'
                if candidate.ready_for_confirmation
                else 'Baseline candidate is blocked pending binding review.'
            ),
            'reason_codes': ['READY_FOR_BASELINE_CONFIRMATION'] if candidate.ready_for_confirmation else ['BINDING_REVIEW_REQUIRED'],
            'blockers': candidate.blockers,
            'metadata': candidate.metadata,
            'linked_binding_artifact': f'baseline_candidate:{candidate.id}',
        },
    )

    if not confirmation.binding_snapshots.exists():
        binding_snapshot = candidate.metadata.get('binding_snapshot') if isinstance(candidate.metadata, dict) else {}

        BaselineBindingSnapshot.objects.create(
            linked_confirmation=confirmation,
            binding_type=BaselineBindingType.CHAMPION_REFERENCE,
            binding_status=BaselineBindingStatus.PREVIOUS,
            binding_snapshot={'reference': candidate.previous_baseline_reference, 'details': (binding_snapshot or {}).get('champion_binding', {})},
            metadata={'source': 'candidate_resolution'},
        )
        BaselineBindingSnapshot.objects.create(
            linked_confirmation=confirmation,
            binding_type=BaselineBindingType.STACK_PROFILE_BINDING,
            binding_status=BaselineBindingStatus.PROPOSED,
            binding_snapshot={'reference': candidate.proposed_baseline_reference, 'details': (binding_snapshot or {}).get('rollout_reference', {})},
            metadata={'source': 'candidate_resolution'},
        )
        BaselineBindingSnapshot.objects.create(
            linked_confirmation=confirmation,
            binding_type=BaselineBindingType.TRUST_CALIBRATION_BINDING,
            binding_status=BaselineBindingStatus.PROPOSED,
            binding_snapshot=(binding_snapshot or {}).get('trust_calibration_binding', {}),
            metadata={'source': 'candidate_resolution'},
        )
        BaselineBindingSnapshot.objects.create(
            linked_confirmation=confirmation,
            binding_type=BaselineBindingType.POLICY_TUNING_BINDING,
            binding_status=BaselineBindingStatus.PROPOSED,
            binding_snapshot=(binding_snapshot or {}).get('policy_tuning_binding', {}),
            metadata={'source': 'candidate_resolution'},
        )

    return confirmation


def confirm_paper_baseline(*, decision_id: int, actor: str = 'operator-ui', rationale: str = '') -> PaperBaselineConfirmation:
    candidate = BaselineConfirmationCandidate.objects.select_related('linked_certification_decision').get(
        linked_certification_decision_id=decision_id
    )
    confirmation = get_or_create_confirmation(candidate=candidate)

    if not candidate.ready_for_confirmation:
        confirmation.confirmation_status = PaperBaselineConfirmationStatus.BLOCKED
        confirmation.blockers = candidate.blockers
        confirmation.save(update_fields=['confirmation_status', 'blockers', 'updated_at'])
        return confirmation

    confirmation.confirmation_status = PaperBaselineConfirmationStatus.CONFIRMED
    confirmation.confirmed_by = actor
    confirmation.confirmed_at = timezone.now()
    confirmation.rationale = rationale or 'Manual operator confirmed paper baseline adoption from certified decision.'
    confirmation.reason_codes = ['MANUAL_BASELINE_CONFIRMATION_APPLIED']
    confirmation.blockers = []
    confirmation.metadata = {**(confirmation.metadata or {}), 'manual_confirmation': True, 'auto_switch_performed': False}
    confirmation.save(
        update_fields=['confirmation_status', 'confirmed_by', 'confirmed_at', 'rationale', 'reason_codes', 'blockers', 'metadata', 'updated_at']
    )

    BaselineBindingSnapshot.objects.create(
        linked_confirmation=confirmation,
        binding_type=BaselineBindingType.STACK_PROFILE_BINDING,
        binding_status=BaselineBindingStatus.CONFIRMED,
        binding_snapshot=confirmation.confirmed_baseline_snapshot,
        metadata={'actor': actor, 'operation': 'manual_confirm'},
    )

    return confirmation
