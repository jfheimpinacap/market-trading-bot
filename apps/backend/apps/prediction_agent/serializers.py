from rest_framework import serializers

from apps.prediction_agent.models import (
    PredictionModelProfile,
    PredictionRun,
    PredictionRuntimeAssessment,
    PredictionRuntimeCandidate,
    PredictionRuntimeRecommendation,
    PredictionRuntimeRun,
    PredictionScore,
    PredictionIntakeRun,
    PredictionIntakeCandidate,
    PredictionConvictionReview,
    RiskReadyPredictionHandoff,
    PredictionIntakeRecommendation,
)


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


class PredictionRuntimeReviewRequestSerializer(serializers.Serializer):
    triggered_by = serializers.CharField(required=False, allow_blank=True, default='manual')


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


class PredictionRuntimeRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = PredictionRuntimeRun
        fields = (
            'id',
            'started_at',
            'completed_at',
            'candidate_count',
            'scored_count',
            'blocked_count',
            'high_edge_count',
            'low_confidence_count',
            'sent_to_risk_count',
            'sent_to_signal_fusion_count',
            'recommendation_summary',
            'active_model_context',
            'metadata',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class PredictionRuntimeCandidateSerializer(serializers.ModelSerializer):
    market_slug = serializers.CharField(source='linked_market.slug', read_only=True)
    market_title = serializers.CharField(source='linked_market.title', read_only=True)

    class Meta:
        model = PredictionRuntimeCandidate
        fields = (
            'id',
            'runtime_run',
            'linked_market',
            'market_slug',
            'market_title',
            'linked_research_candidate',
            'linked_scan_signals',
            'market_provider',
            'category',
            'market_probability',
            'narrative_support_score',
            'divergence_score',
            'research_status',
            'candidate_quality_score',
            'metadata',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class PredictionRuntimeAssessmentSerializer(serializers.ModelSerializer):
    candidate = PredictionRuntimeCandidateSerializer(source='linked_candidate', read_only=True)

    class Meta:
        model = PredictionRuntimeAssessment
        fields = (
            'id',
            'linked_candidate',
            'candidate',
            'active_model_name',
            'model_mode',
            'system_probability',
            'calibrated_probability',
            'market_probability',
            'raw_edge',
            'adjusted_edge',
            'confidence_score',
            'uncertainty_score',
            'evidence_quality_score',
            'precedent_caution_score',
            'narrative_influence_score',
            'prediction_status',
            'rationale',
            'reason_codes',
            'feature_summary',
            'metadata',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class PredictionRuntimeRecommendationSerializer(serializers.ModelSerializer):
    assessment = PredictionRuntimeAssessmentSerializer(source='target_assessment', read_only=True)

    class Meta:
        model = PredictionRuntimeRecommendation
        fields = (
            'id',
            'runtime_run',
            'target_assessment',
            'assessment',
            'recommendation_type',
            'rationale',
            'reason_codes',
            'confidence',
            'blockers',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class PredictionIntakeRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = PredictionIntakeRun
        fields = '__all__'


class PredictionIntakeCandidateSerializer(serializers.ModelSerializer):
    market_slug = serializers.CharField(source='linked_market.slug', read_only=True)
    market_title = serializers.CharField(source='linked_market.title', read_only=True)

    class Meta:
        model = PredictionIntakeCandidate
        fields = '__all__'


class PredictionConvictionReviewSerializer(serializers.ModelSerializer):
    intake_candidate = PredictionIntakeCandidateSerializer(source='linked_intake_candidate', read_only=True)

    class Meta:
        model = PredictionConvictionReview
        fields = '__all__'


class RiskReadyPredictionHandoffSerializer(serializers.ModelSerializer):
    market_slug = serializers.CharField(source='linked_market.slug', read_only=True)
    market_title = serializers.CharField(source='linked_market.title', read_only=True)

    class Meta:
        model = RiskReadyPredictionHandoff
        fields = '__all__'


class PredictionIntakeRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PredictionIntakeRecommendation
        fields = '__all__'
