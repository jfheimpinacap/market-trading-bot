from django.core.exceptions import ValidationError

from apps.certification_board.models import CertificationDecisionLog, CertificationLevel, CertificationRun
from apps.runtime_governor.models import RuntimeMode
from apps.runtime_governor.services.governance import set_runtime_mode


def apply_certification_decision(*, run: CertificationRun, actor: str, apply_safe_state: bool = False, notes: str = '') -> CertificationRun:
    if not apply_safe_state:
        CertificationDecisionLog.objects.create(
            run=run,
            event_type='MANUAL_REVIEW_NOTED',
            actor=actor,
            notes=notes or 'Manual review completed. No automatic state change applied.',
            payload={'apply_safe_state': False},
        )
        return run

    if run.certification_level in {CertificationLevel.PAPER_CERTIFIED_BALANCED, CertificationLevel.PAPER_CERTIFIED_HIGH_AUTONOMY}:
        raise ValidationError('Safe apply supports only conservative runtime changes in this paper-only phase.')

    mode = RuntimeMode.PAPER_ASSIST
    if run.certification_level == CertificationLevel.PAPER_CERTIFIED_DEFENSIVE:
        mode = RuntimeMode.PAPER_SEMI_AUTO

    result = set_runtime_mode(
        requested_mode=mode,
        set_by='operator',
        rationale='Applied conservative certification envelope manually.',
        metadata={'source': 'certification_board', 'run_id': run.id},
    )
    CertificationDecisionLog.objects.create(
        run=run,
        event_type='SAFE_APPLY_EXECUTED',
        actor=actor,
        notes=notes or 'Manual safe apply executed for paper runtime constraints.',
        payload={'apply_safe_state': True, 'runtime_changed': result.get('changed', False), 'target_mode': mode},
    )
    return run
