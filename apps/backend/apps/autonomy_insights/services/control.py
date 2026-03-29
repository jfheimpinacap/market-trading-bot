from __future__ import annotations

from django.utils import timezone

from apps.autonomy_insights.models import CampaignInsight


def mark_insight_reviewed(*, insight_id: int, actor: str = 'operator-ui') -> CampaignInsight:
    insight = CampaignInsight.objects.get(id=insight_id)
    insight.reviewed = True
    insight.reviewed_by = actor
    insight.reviewed_at = timezone.now()
    insight.metadata = {**(insight.metadata or {}), 'reviewed_manually': True}
    insight.save(update_fields=['reviewed', 'reviewed_by', 'reviewed_at', 'metadata', 'updated_at'])
    return insight
