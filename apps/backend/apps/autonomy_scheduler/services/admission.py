from django.utils import timezone

from apps.autonomy_program.models import ProgramConcurrencyPosture
from apps.autonomy_program.services.state import build_program_state_payload
from apps.autonomy_scheduler.models import CampaignAdmission, CampaignAdmissionStatus, ChangeWindowStatus


def evaluate_admission(admission: CampaignAdmission, *, active_window, critical_incident_active: bool, locked_domains: list[str]) -> dict:
    campaign = admission.campaign
    metadata = campaign.metadata or {}
    blockers: list[str] = []
    reason_codes: list[str] = []

    state = build_program_state_payload()['state']
    posture = state.concurrency_posture
    if posture == ProgramConcurrencyPosture.FROZEN:
        blockers.append('Program is frozen')
        reason_codes.append('PROGRAM_FROZEN')
    if posture == ProgramConcurrencyPosture.HIGH_RISK:
        blockers.append('Program is high risk; new admissions restricted')
        reason_codes.append('PROGRAM_HIGH_RISK')
    if critical_incident_active:
        blockers.append('Critical incident active')
        reason_codes.append('CRITICAL_INCIDENT_ACTIVE')

    domains = metadata.get('domains', []) if isinstance(metadata.get('domains', []), list) else []
    overlap = sorted(set(domains) & set(locked_domains or []))
    if overlap:
        blockers.append(f'Campaign conflicts with locked/observing domains: {", ".join(overlap)}')
        reason_codes.append('DOMAIN_LOCKED')

    if active_window is None:
        blockers.append('No safe-start window is open')
        reason_codes.append('WAIT_FOR_WINDOW')
    elif active_window.status != ChangeWindowStatus.OPEN:
        blockers.append(f'Active window is {active_window.status}')
        reason_codes.append('WINDOW_NOT_OPEN')

    if admission.deferred_until and admission.deferred_until > timezone.now():
        blockers.append('Deferred until future date')
        reason_codes.append('DEFERRED_UNTIL_ACTIVE')

    dependencies = metadata.get('depends_on_campaigns', []) if isinstance(metadata.get('depends_on_campaigns', []), list) else []
    if dependencies:
        unresolved = [item for item in dependencies if not CampaignAdmission.objects.filter(campaign_id=item, status=CampaignAdmissionStatus.ADMITTED).exists()]
        if unresolved:
            blockers.append('Dependency campaigns are not admitted/stable')
            reason_codes.append('DEPENDENCY_NOT_STABLE')

    if blockers:
        admission.status = CampaignAdmissionStatus.DEFERRED if 'DEPENDENCY_NOT_STABLE' in reason_codes else CampaignAdmissionStatus.BLOCKED
    else:
        admission.status = CampaignAdmissionStatus.READY
    admission.blocked_reasons = blockers
    admission.save(update_fields=['status', 'blocked_reasons', 'updated_at'])

    return {'posture': posture, 'blockers': blockers, 'reason_codes': reason_codes, 'domains': domains}
