from rest_framework import serializers

from apps.memory_retrieval.models import AgentPrecedentUse, MemoryDocument, MemoryQueryType, MemoryRetrievalRun, RetrievedPrecedent
from apps.memory_retrieval.services.precedents import build_precedent_summary


class MemoryDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = MemoryDocument
        fields = (
            'id',
            'document_type',
            'source_app',
            'source_object_id',
            'title',
            'text_content',
            'structured_summary',
            'tags',
            'metadata',
            'embedding_model',
            'embedded_at',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class RetrievedPrecedentSerializer(serializers.ModelSerializer):
    memory_document = MemoryDocumentSerializer(read_only=True)

    class Meta:
        model = RetrievedPrecedent
        fields = ('id', 'retrieval_run', 'memory_document', 'similarity_score', 'rank', 'short_reason', 'created_at', 'updated_at')
        read_only_fields = fields


class MemoryRetrievalRunSerializer(serializers.ModelSerializer):
    precedents = RetrievedPrecedentSerializer(many=True, read_only=True)

    class Meta:
        model = MemoryRetrievalRun
        fields = (
            'id',
            'query_text',
            'query_type',
            'context_metadata',
            'result_count',
            'metadata',
            'created_at',
            'updated_at',
            'precedents',
        )
        read_only_fields = fields


class MemoryIndexRequestSerializer(serializers.Serializer):
    sources = serializers.ListField(child=serializers.CharField(), required=False)
    force_reembed = serializers.BooleanField(default=False, required=False)


class MemoryRetrieveRequestSerializer(serializers.Serializer):
    query_text = serializers.CharField()
    query_type = serializers.ChoiceField(choices=MemoryQueryType.choices, default=MemoryQueryType.MANUAL, required=False)
    context_metadata = serializers.JSONField(required=False)
    limit = serializers.IntegerField(default=8, min_value=1, max_value=25, required=False)
    min_similarity = serializers.FloatField(default=0.55, min_value=0.0, max_value=1.0, required=False)


class MemorySummarySerializer(serializers.Serializer):
    documents_indexed = serializers.IntegerField()
    retrieval_runs = serializers.IntegerField()
    document_types = serializers.DictField(child=serializers.IntegerField())
    source_apps = serializers.DictField(child=serializers.IntegerField())
    last_indexed_document_at = serializers.DateTimeField(allow_null=True)
    last_retrieval_run = MemoryRetrievalRunSerializer(allow_null=True)


class MemoryPrecedentSummarySerializer(serializers.Serializer):
    retrieval_run_id = serializers.IntegerField()
    query_text = serializers.CharField()
    query_type = serializers.CharField()
    matches = serializers.IntegerField()
    average_similarity = serializers.FloatField(allow_null=True)
    most_similar_cases = serializers.JSONField()
    by_document_type = serializers.DictField(child=serializers.IntegerField())
    prior_caution_signals = serializers.ListField(child=serializers.CharField())
    prior_failure_modes = serializers.ListField(child=serializers.CharField())
    lessons_learned = serializers.ListField(child=serializers.CharField())


class MemoryRunWithSummarySerializer(serializers.Serializer):
    run = MemoryRetrievalRunSerializer()
    summary = MemoryPrecedentSummarySerializer()


class AgentPrecedentUseSerializer(serializers.ModelSerializer):
    retrieval_run = MemoryRetrievalRunSerializer(read_only=True)

    class Meta:
        model = AgentPrecedentUse
        fields = (
            'id',
            'agent_name',
            'source_app',
            'source_object_id',
            'retrieval_run',
            'precedent_count',
            'influence_mode',
            'metadata',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class MemoryInfluenceSummarySerializer(serializers.Serializer):
    retrieval_run_id = serializers.IntegerField()
    influence_mode = serializers.CharField()
    precedent_confidence = serializers.FloatField()
    caution_flags = serializers.ListField(child=serializers.CharField())
    summary = MemoryPrecedentSummarySerializer()
    agent_use_id = serializers.IntegerField(allow_null=True)


def serialize_run_with_summary(run: MemoryRetrievalRun) -> dict:
    return MemoryRunWithSummarySerializer({'run': run, 'summary': build_precedent_summary(run)}).data
