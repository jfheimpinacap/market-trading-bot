from rest_framework import serializers

from apps.postmortem_agents.models import PostmortemAgentReview, PostmortemBoardConclusion, PostmortemBoardRun


class PostmortemBoardRunSerializer(serializers.ModelSerializer):
    trade_review_id = serializers.IntegerField(source='related_trade_review_id', read_only=True)
    trade_id = serializers.IntegerField(source='related_trade_review.paper_trade_id', read_only=True)
    market_id = serializers.IntegerField(source='related_trade_review.market_id', read_only=True)

    class Meta:
        model = PostmortemBoardRun
        fields = (
            'id',
            'related_trade_review',
            'trade_review_id',
            'trade_id',
            'market_id',
            'status',
            'started_at',
            'finished_at',
            'perspectives_run_count',
            'summary',
            'details',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class PostmortemAgentReviewSerializer(serializers.ModelSerializer):
    board_run_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = PostmortemAgentReview
        fields = (
            'id',
            'board_run',
            'board_run_id',
            'perspective_type',
            'status',
            'conclusion',
            'key_findings',
            'confidence',
            'recommended_actions',
            'metadata',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class PostmortemBoardConclusionSerializer(serializers.ModelSerializer):
    board_run_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = PostmortemBoardConclusion
        fields = (
            'id',
            'board_run',
            'board_run_id',
            'primary_failure_mode',
            'secondary_failure_modes',
            'lesson_learned',
            'recommended_adjustments',
            'should_update_learning_memory',
            'severity',
            'metadata',
            'created_at',
        )
        read_only_fields = fields


class PostmortemBoardRunRequestSerializer(serializers.Serializer):
    related_trade_review_id = serializers.IntegerField(required=True)
    triggered_from = serializers.ChoiceField(choices=['manual', 'automation', 'continuous_demo'], default='manual', required=False)
    force_learning_rebuild = serializers.BooleanField(required=False, default=False)
