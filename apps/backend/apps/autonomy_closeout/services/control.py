from __future__ import annotations

from django.utils import timezone

from apps.autonomy_closeout.models import CampaignCloseoutReport, CampaignCloseoutStatus


def complete_closeout(*, report: CampaignCloseoutReport, actor: str) -> CampaignCloseoutReport:
    blockers = report.major_blockers or []
    unresolved_approvals = int(report.metadata.get('unresolved_approvals_count', 0))
    if blockers or unresolved_approvals > 0:
        raise ValueError('Closeout cannot be completed while blockers or critical approvals remain open.')

    report.closeout_status = CampaignCloseoutStatus.COMPLETED
    report.closed_out_by = actor
    report.closed_out_at = timezone.now()
    report.metadata = {**report.metadata, 'completed_manually': True, 'completed_by': actor}
    report.save(update_fields=['closeout_status', 'closed_out_by', 'closed_out_at', 'metadata', 'updated_at'])
    return report
