from rest_framework import serializers


class LlmStatusSerializer(serializers.Serializer):
    enabled = serializers.BooleanField()
    provider = serializers.CharField()
    ollama_base_url = serializers.CharField()
    chat_model = serializers.CharField()
    embed_model = serializers.CharField()
    timeout_seconds = serializers.IntegerField()
    reachable = serializers.BooleanField()
    status = serializers.CharField()
    message = serializers.CharField()


class ProposalThesisRequestSerializer(serializers.Serializer):
    proposal_id = serializers.IntegerField(required=False)
    market_title = serializers.CharField(required=False, allow_blank=True)
    headline = serializers.CharField(required=False, allow_blank=True)
    thesis = serializers.CharField(required=False, allow_blank=True)
    rationale = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if not attrs.get('proposal_id') and not any(attrs.get(field) for field in ('market_title', 'headline', 'thesis', 'rationale')):
            raise serializers.ValidationError('Provide proposal_id or narrative context fields.')
        return attrs


class PostmortemSummaryRequestSerializer(serializers.Serializer):
    review_id = serializers.IntegerField(required=False)
    summary = serializers.CharField(required=False, allow_blank=True)
    rationale = serializers.CharField(required=False, allow_blank=True)
    lesson = serializers.CharField(required=False, allow_blank=True)
    recommendation = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if not attrs.get('review_id') and not any(attrs.get(field) for field in ('summary', 'rationale', 'lesson', 'recommendation')):
            raise serializers.ValidationError('Provide review_id or post-mortem text fields.')
        return attrs


class LearningNoteRequestSerializer(serializers.Serializer):
    memory_entry_id = serializers.IntegerField(required=False)
    summary = serializers.CharField(required=False, allow_blank=True)
    rationale = serializers.CharField(required=False, allow_blank=True)
    outcome = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if not attrs.get('memory_entry_id') and not any(attrs.get(field) for field in ('summary', 'rationale', 'outcome')):
            raise serializers.ValidationError('Provide memory_entry_id or text context fields.')
        return attrs


class EmbedRequestSerializer(serializers.Serializer):
    text = serializers.CharField(required=False, allow_blank=False)
    texts = serializers.ListField(child=serializers.CharField(allow_blank=False), required=False, allow_empty=False)

    def validate(self, attrs):
        has_text = 'text' in attrs
        has_texts = 'texts' in attrs
        if has_text == has_texts:
            raise serializers.ValidationError('Provide either text or texts (batch), but not both.')
        return attrs
