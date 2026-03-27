from django.db import models

from apps.common.models import TimeStampedModel


class MemoryDocumentType(models.TextChoices):
    LEARNING_NOTE = 'learning_note', 'Learning note'
    POSTMORTEM_CONCLUSION = 'postmortem_conclusion', 'Postmortem conclusion'
    POSTMORTEM_PERSPECTIVE = 'postmortem_perspective', 'Postmortem perspective'
    RESEARCH_CANDIDATE_SNAPSHOT = 'research_candidate_snapshot', 'Research candidate snapshot'
    PREDICTION_SCORE_SNAPSHOT = 'prediction_score_snapshot', 'Prediction score snapshot'
    RISK_ASSESSMENT_SNAPSHOT = 'risk_assessment_snapshot', 'Risk assessment snapshot'
    REPLAY_SUMMARY = 'replay_summary', 'Replay summary'
    EXPERIMENT_RESULT = 'experiment_result', 'Experiment result'
    READINESS_ASSESSMENT = 'readiness_assessment', 'Readiness assessment'
    LIFECYCLE_DECISION = 'lifecycle_decision', 'Lifecycle decision'
    EXECUTION_IMPACT_SUMMARY = 'execution_impact_summary', 'Execution impact summary'
    TRADE_REVIEW = 'trade_review', 'Trade review'


class MemoryQueryType(models.TextChoices):
    RESEARCH = 'research', 'Research'
    PREDICTION = 'prediction', 'Prediction'
    RISK = 'risk', 'Risk'
    POSTMORTEM = 'postmortem', 'Postmortem'
    LIFECYCLE = 'lifecycle', 'Lifecycle'
    MANUAL = 'manual', 'Manual'


class MemoryDocument(TimeStampedModel):
    document_type = models.CharField(max_length=48, choices=MemoryDocumentType.choices)
    source_app = models.CharField(max_length=64)
    source_object_id = models.CharField(max_length=128)
    title = models.CharField(max_length=255)
    text_content = models.TextField()
    structured_summary = models.JSONField(default=dict, blank=True)
    tags = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    embedding = models.JSONField(default=list, blank=True)
    embedding_model = models.CharField(max_length=96, blank=True)
    embedded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        constraints = [
            models.UniqueConstraint(fields=['source_app', 'source_object_id', 'document_type'], name='memory_doc_source_unique')
        ]
        indexes = [
            models.Index(fields=['document_type', '-created_at']),
            models.Index(fields=['source_app', '-created_at']),
        ]


class MemoryRetrievalRun(TimeStampedModel):
    query_text = models.TextField()
    query_type = models.CharField(max_length=24, choices=MemoryQueryType.choices, default=MemoryQueryType.MANUAL)
    context_metadata = models.JSONField(default=dict, blank=True)
    result_count = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class RetrievedPrecedent(TimeStampedModel):
    retrieval_run = models.ForeignKey(MemoryRetrievalRun, on_delete=models.CASCADE, related_name='precedents')
    memory_document = models.ForeignKey(MemoryDocument, on_delete=models.PROTECT, related_name='retrieved_precedents')
    similarity_score = models.FloatField(default=0)
    rank = models.PositiveIntegerField(default=1)
    short_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['rank', 'id']
        constraints = [
            models.UniqueConstraint(fields=['retrieval_run', 'rank'], name='memory_precedent_rank_unique')
        ]
