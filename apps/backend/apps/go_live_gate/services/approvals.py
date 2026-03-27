from apps.go_live_gate.models import GoLiveApprovalRequest, GoLiveApprovalStatus, GoLiveChecklistRun


def create_approval_request(
    requested_by: str,
    rationale: str,
    scope: str,
    requested_mode: str,
    blocking_reasons: list[str] | None = None,
    checklist_run: GoLiveChecklistRun | None = None,
    metadata: dict | None = None,
) -> GoLiveApprovalRequest:
    return GoLiveApprovalRequest.objects.create(
        requested_by=requested_by,
        rationale=rationale,
        scope=scope,
        requested_mode=requested_mode,
        status=GoLiveApprovalStatus.PENDING,
        blocking_reasons=blocking_reasons or [],
        checklist_run=checklist_run,
        metadata=metadata or {},
    )
