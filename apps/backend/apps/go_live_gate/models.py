from django.db import models

from apps.common.models import TimeStampedModel


class GoLiveGateStateCode(models.TextChoices):
    PAPER_ONLY_LOCKED = 'PAPER_ONLY_LOCKED', 'Paper only locked'
    PRELIVE_REHEARSAL_READY = 'PRELIVE_REHEARSAL_READY', 'Pre-live rehearsal ready'
    MANUAL_APPROVAL_PENDING = 'MANUAL_APPROVAL_PENDING', 'Manual approval pending'
    LIVE_DISABLED_BY_POLICY = 'LIVE_DISABLED_BY_POLICY', 'Live disabled by policy'
    REMEDIATION_REQUIRED = 'REMEDIATION_REQUIRED', 'Remediation required'


class GoLiveApprovalStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    PENDING = 'PENDING', 'Pending'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'
    EXPIRED = 'EXPIRED', 'Expired'


class CapitalFirewallRule(TimeStampedModel):
    code = models.CharField(max_length=64, unique=True)
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    enabled = models.BooleanField(default=True)
    block_live_transition = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['code', 'id']


class GoLiveChecklistRun(TimeStampedModel):
    requested_by = models.CharField(max_length=120, default='local-operator')
    context = models.CharField(max_length=64, default='manual')
    checklist_version = models.CharField(max_length=24, default='v1')
    passed = models.BooleanField(default=False)
    gate_state = models.CharField(max_length=40, choices=GoLiveGateStateCode.choices, default=GoLiveGateStateCode.PAPER_ONLY_LOCKED)
    passed_items = models.JSONField(default=list, blank=True)
    failed_items = models.JSONField(default=list, blank=True)
    blocking_reasons = models.JSONField(default=list, blank=True)
    evidence = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class GoLiveApprovalRequest(TimeStampedModel):
    requested_by = models.CharField(max_length=120)
    rationale = models.TextField(blank=True)
    scope = models.CharField(max_length=120, default='global')
    requested_mode = models.CharField(max_length=48, default='PRELIVE_REHEARSAL')
    status = models.CharField(max_length=16, choices=GoLiveApprovalStatus.choices, default=GoLiveApprovalStatus.DRAFT)
    blocking_reasons = models.JSONField(default=list, blank=True)
    checklist_run = models.ForeignKey(GoLiveChecklistRun, null=True, blank=True, on_delete=models.SET_NULL, related_name='approval_requests')
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class GoLiveRehearsalRun(TimeStampedModel):
    intent = models.ForeignKey('broker_bridge.BrokerOrderIntent', on_delete=models.PROTECT, related_name='go_live_rehearsals')
    checklist_run = models.ForeignKey(GoLiveChecklistRun, null=True, blank=True, on_delete=models.SET_NULL, related_name='rehearsals')
    approval_request = models.ForeignKey(GoLiveApprovalRequest, null=True, blank=True, on_delete=models.SET_NULL, related_name='rehearsals')
    gate_state = models.CharField(max_length=40, choices=GoLiveGateStateCode.choices, default=GoLiveGateStateCode.PAPER_ONLY_LOCKED)
    allowed_to_proceed_in_rehearsal = models.BooleanField(default=False)
    blocked_by_firewall = models.BooleanField(default=True)
    missing_approvals = models.JSONField(default=list, blank=True)
    missing_preconditions = models.JSONField(default=list, blank=True)
    blocked_reasons = models.JSONField(default=list, blank=True)
    final_dry_run_disposition = models.CharField(max_length=32, blank=True)
    dry_run_reference_id = models.PositiveIntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
