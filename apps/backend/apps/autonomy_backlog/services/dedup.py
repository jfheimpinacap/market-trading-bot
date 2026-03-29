from __future__ import annotations

from apps.autonomy_backlog.models import GovernanceBacklogItem


def find_duplicate_backlog_item(*, artifact_id: int) -> GovernanceBacklogItem | None:
    return GovernanceBacklogItem.objects.filter(advisory_artifact_id=artifact_id).order_by('-updated_at', '-id').first()
