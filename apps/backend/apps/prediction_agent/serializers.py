from rest_framework import serializers

from apps.prediction_agent.models import PredictionModelProfile, PredictionRun, PredictionScore


class PredictionModelProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PredictionModelProfile
        fields = (
            'id',
            'slug',
            'name',
            'description',
            'is_active',
            'use_narrative',
            'use_learning',
            'calibration_alpha',
            'calibration_beta',
            'confidence_floor',
            'confidence_cap',
            'edge_strong_threshold',
            'edge_neutral_threshold',
            'weights',
            'metadata',
            'created_at',
            'updated_at',
        )


class PredictionScoreRequestSerializer(serializers.Serializer):
    market_id = serializers.IntegerField(min_value=1)
    profile_slug = serializers.CharField(required=False, allow_blank=True)
    triggered_by = serializers.CharField(required=False, allow_blank=True, default='api')


class PredictionRunSerializer(serializers.ModelSerializer):
    profile_slug = serializers.CharField(source='model_profile.slug', read_only=True)

    class Meta:
        model = PredictionRun
        fields = (
            'id',
            'status',
            'triggered_by',
            'profile_slug',
            'started_at',
            'finished_at',
            'markets_scored',
            'errors',
            'metadata',
            'created_at',
            'updated_at',
        )


class PredictionScoreSerializer(serializers.ModelSerializer):
    market_slug = serializers.CharField(source='market.slug', read_only=True)
    market_title = serializers.CharField(source='market.title', read_only=True)
    profile_slug = serializers.CharField(source='model_profile.slug', read_only=True)
    run = PredictionRunSerializer(read_only=True)

    class Meta:
        model = PredictionScore
        fields = (
            'id',
            'run',
            'market',
            'market_slug',
            'market_title',
            'profile_slug',
            'market_probability',
            'system_probability',
            'edge',
            'edge_label',
            'confidence',
            'confidence_level',
            'rationale',
            'narrative_contribution',
            'model_profile_used',
            'details',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields
