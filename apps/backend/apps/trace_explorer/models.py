from django.db import models

from apps.common.models import TimeStampedModel


class TraceRoot(TimeStampedModel):
    root_type = models.CharField(max_length=48)
    root_object_id = models.CharField(max_length=128)
    label = models.CharField(max_length=255, blank=True)
    current_status = models.CharField(max_length=64, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-updated_at', '-id']
        constraints = [
            models.UniqueConstraint(fields=['root_type', 'root_object_id'], name='trace_root_type_object_unique'),
        ]
        indexes = [
            models.Index(fields=['root_type', '-updated_at']),
        ]


class TraceNode(TimeStampedModel):
    trace_root = models.ForeignKey(TraceRoot, on_delete=models.CASCADE, related_name='nodes')
    node_key = models.CharField(max_length=160)
    node_type = models.CharField(max_length=64)
    stage = models.CharField(max_length=32, blank=True)
    ref_type = models.CharField(max_length=64, blank=True)
    ref_id = models.CharField(max_length=128, blank=True)
    title = models.CharField(max_length=255)
    status = models.CharField(max_length=64, blank=True)
    summary = models.TextField(blank=True)
    happened_at = models.DateTimeField(null=True, blank=True)
    snapshot = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['happened_at', 'id']
        constraints = [
            models.UniqueConstraint(fields=['trace_root', 'node_key'], name='trace_node_unique_per_root_key'),
        ]
        indexes = [
            models.Index(fields=['trace_root', 'stage']),
            models.Index(fields=['ref_type', 'ref_id']),
        ]


class TraceEdge(TimeStampedModel):
    trace_root = models.ForeignKey(TraceRoot, on_delete=models.CASCADE, related_name='edges')
    from_node = models.ForeignKey(TraceNode, on_delete=models.CASCADE, related_name='outgoing_edges')
    to_node = models.ForeignKey(TraceNode, on_delete=models.CASCADE, related_name='incoming_edges')
    relation = models.CharField(max_length=48)
    summary = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['id']
        indexes = [
            models.Index(fields=['trace_root', 'relation']),
        ]


class TraceQueryRunStatus(models.TextChoices):
    SUCCESS = 'SUCCESS', 'Success'
    PARTIAL = 'PARTIAL', 'Partial'
    FAILED = 'FAILED', 'Failed'


class TraceQueryRun(TimeStampedModel):
    root = models.ForeignKey(TraceRoot, null=True, blank=True, on_delete=models.SET_NULL, related_name='query_runs')
    query_type = models.CharField(max_length=48, default='root_lookup')
    query_payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=12, choices=TraceQueryRunStatus.choices, default=TraceQueryRunStatus.SUCCESS)
    partial = models.BooleanField(default=False)
    node_count = models.PositiveIntegerField(default=0)
    edge_count = models.PositiveIntegerField(default=0)
    summary = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['status', '-created_at']),
        ]
