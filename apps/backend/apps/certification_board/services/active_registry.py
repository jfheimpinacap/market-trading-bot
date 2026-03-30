from __future__ import annotations

from apps.certification_board.models import ActivePaperBindingRecord, ActivePaperBindingStatus, PaperBaselineActivation


def set_active_paper_binding(
    *,
    target_component: str,
    target_scope: str,
    active_binding_type: str,
    active_snapshot: dict,
    activation: PaperBaselineActivation,
    metadata: dict | None = None,
) -> ActivePaperBindingRecord:
    previous = ActivePaperBindingRecord.objects.filter(
        target_component=target_component,
        target_scope=target_scope,
        active_binding_type=active_binding_type,
        status=ActivePaperBindingStatus.ACTIVE,
    ).order_by('-updated_at', '-id')

    for row in previous:
        row.status = ActivePaperBindingStatus.SUPERSEDED
        row.metadata = {**(row.metadata or {}), 'superseded_by_activation_id': activation.id}
        row.save(update_fields=['status', 'metadata', 'updated_at'])

    return ActivePaperBindingRecord.objects.create(
        target_component=target_component,
        target_scope=target_scope,
        active_binding_type=active_binding_type,
        active_snapshot=active_snapshot,
        source_activation=activation,
        status=ActivePaperBindingStatus.ACTIVE,
        metadata=metadata or {},
    )
