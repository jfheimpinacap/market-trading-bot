from rest_framework import serializers

from apps.opportunity_supervisor.models import (
    OpportunityCycleItem,
    OpportunityCycleRun,
    OpportunityCycleRuntimeRun,
    OpportunityExecutionPlan,
    OpportunityFusionAssessment,
    OpportunityFusionCandidate,
    OpportunityRecommendation,
    PaperOpportunityProposal,
)


class OpportunityExecutionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpportunityExecutionPlan
        fields = (
            'id',
            'item',
            'proposal',
            'queue_item',
            'paper_trade',
            'allocation_quantity',
            'runtime_mode',
            'policy_decision',
            'safety_status',
            'queue_required',
            'auto_execute_allowed',
            'final_recommended_action',
            'explanation',
            'metadata',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class OpportunityCycleItemSerializer(serializers.ModelSerializer):
    market_title = serializers.CharField(source='market.title', read_only=True)
    market_slug = serializers.CharField(source='market.slug', read_only=True)
    execution_plan = OpportunityExecutionPlanSerializer(read_only=True)

    class Meta:
        model = OpportunityCycleItem
        fields = (
            'id',
            'run',
            'market',
            'market_title',
            'market_slug',
            'source_provider',
            'research_context',
            'prediction_context',
            'risk_context',
            'signal_context',
            'proposal',
            'proposal_status',
            'allocation_status',
            'allocation_quantity',
            'execution_path',
            'rationale',
            'metadata',
            'execution_plan',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class OpportunityCycleRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpportunityCycleRun
        fields = (
            'id',
            'status',
            'profile_slug',
            'started_at',
            'finished_at',
            'markets_scanned',
            'opportunities_built',
            'proposals_generated',
            'allocation_ready_count',
            'queued_count',
            'auto_executed_count',
            'blocked_count',
            'summary',
            'details',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class RunOpportunityCycleSerializer(serializers.Serializer):
    profile_slug = serializers.CharField(required=False, allow_blank=False, max_length=64)


class OpportunityFusionCandidateSerializer(serializers.ModelSerializer):
    market_title = serializers.CharField(source='linked_market.title', read_only=True)

    class Meta:
        model = OpportunityFusionCandidate
        fields = '__all__'


class OpportunityFusionAssessmentSerializer(serializers.ModelSerializer):
    market = serializers.IntegerField(source='linked_candidate.linked_market_id', read_only=True)
    market_title = serializers.CharField(source='linked_candidate.linked_market.title', read_only=True)
    provider = serializers.CharField(source='linked_candidate.provider', read_only=True)
    category = serializers.CharField(source='linked_candidate.category', read_only=True)
    calibrated_probability = serializers.DecimalField(
        source='linked_candidate.linked_prediction_assessment.calibrated_probability',
        max_digits=7,
        decimal_places=4,
        read_only=True,
        allow_null=True,
    )
    adjusted_edge = serializers.DecimalField(source='linked_candidate.adjusted_edge', max_digits=8, decimal_places=4, read_only=True)
    risk_clearance = serializers.CharField(source='linked_candidate.linked_risk_approval.approval_status', read_only=True)

    class Meta:
        model = OpportunityFusionAssessment
        fields = '__all__'


class PaperOpportunityProposalSerializer(serializers.ModelSerializer):
    market_title = serializers.CharField(source='linked_assessment.linked_candidate.linked_market.title', read_only=True)

    class Meta:
        model = PaperOpportunityProposal
        fields = '__all__'


class OpportunityRecommendationSerializer(serializers.ModelSerializer):
    market_title = serializers.CharField(source='target_assessment.linked_candidate.linked_market.title', read_only=True)

    class Meta:
        model = OpportunityRecommendation
        fields = '__all__'


class OpportunityCycleRuntimeRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpportunityCycleRuntimeRun
        fields = '__all__'
