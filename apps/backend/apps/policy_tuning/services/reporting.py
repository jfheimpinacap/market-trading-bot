from datetime import timedelta

from django.db.models import Count
from django.utils import timezone

from apps.policy_tuning.models import PolicyTuningApplicationLog, PolicyTuningCandidate, PolicyTuningCandidateStatus


def build_policy_tuning_summary() -> dict:
    status_counts = {
        row['status']: row['count']
        for row in PolicyTuningCandidate.objects.values('status').annotate(count=Count('id'))
    }
    recent_cutoff = timezone.now() - timedelta(days=7)
    recent_applied = PolicyTuningApplicationLog.objects.filter(applied_at__gte=recent_cutoff).count()

    return {
        'total_candidates': PolicyTuningCandidate.objects.count(),
        'pending_candidates': status_counts.get(PolicyTuningCandidateStatus.PENDING_APPROVAL, 0),
        'approved_not_applied': status_counts.get(PolicyTuningCandidateStatus.APPROVED, 0),
        'applied_recently': recent_applied,
        'rejected_or_superseded': status_counts.get(PolicyTuningCandidateStatus.REJECTED, 0)
        + status_counts.get(PolicyTuningCandidateStatus.SUPERSEDED, 0),
        'status_breakdown': status_counts,
        'latest_application': PolicyTuningApplicationLog.objects.values('id', 'candidate_id', 'applied_at').order_by('-applied_at', '-id').first(),
    }
