from rest_framework import serializers

from apps.portfolio_governor.models import (
    PortfolioExposureClusterSnapshot,
    PortfolioExposureConflictReview,
    PortfolioExposureCoordinationRun,
    PortfolioExposureDecision,
    PortfolioExposureRecommendation,
    PortfolioExposureSnapshot,
    PortfolioGovernanceRun,
    PortfolioThrottleDecision,
    SessionExposureContribution,
)


class PortfolioExposureSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortfolioExposureSnapshot
        fields = (
            'id',
            'total_equity',
            'available_cash',
            'total_exposure',
            'open_positions',
            'unrealized_pnl',
            'recent_drawdown_pct',
            'cash_reserve_ratio',
            'concentration_market_ratio',
            'concentration_provider_ratio',
            'exposure_by_market',
            'exposure_by_provider',
            'exposure_by_category',
            'created_at_snapshot',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class PortfolioThrottleDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortfolioThrottleDecision
        fields = (
            'id',
            'state',
            'rationale',
            'reason_codes',
            'recommended_max_new_positions',
            'recommended_max_size_multiplier',
            'regime_signals',
            'metadata',
            'created_at_decision',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class PortfolioGovernanceRunSerializer(serializers.ModelSerializer):
    exposure_snapshot = PortfolioExposureSnapshotSerializer(read_only=True)
    throttle_decision = PortfolioThrottleDecisionSerializer(read_only=True)

    class Meta:
        model = PortfolioGovernanceRun
        fields = (
            'id',
            'status',
            'profile_slug',
            'started_at',
            'finished_at',
            'summary',
            'details',
            'exposure_snapshot',
            'throttle_decision',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class RunPortfolioGovernanceSerializer(serializers.Serializer):
    profile_slug = serializers.CharField(required=False, allow_blank=False, max_length=64)


class PortfolioExposureCoordinationRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortfolioExposureCoordinationRun
        fields = '__all__'
        read_only_fields = (
            'id', 'started_at', 'completed_at', 'considered_cluster_count', 'concentration_alert_count',
            'conflict_alert_count', 'throttle_count', 'defer_count', 'park_count', 'manual_review_count',
            'recommendation_summary', 'metadata', 'created_at', 'updated_at',
        )


class PortfolioExposureClusterSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortfolioExposureClusterSnapshot
        fields = '__all__'


class SessionExposureContributionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SessionExposureContribution
        fields = '__all__'


class PortfolioExposureConflictReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortfolioExposureConflictReview
        fields = '__all__'


class PortfolioExposureDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortfolioExposureDecision
        fields = '__all__'


class PortfolioExposureRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortfolioExposureRecommendation
        fields = '__all__'
