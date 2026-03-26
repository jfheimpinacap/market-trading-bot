from rest_framework import serializers

from apps.opportunity_supervisor.models import OpportunityCycleItem, OpportunityCycleRun, OpportunityExecutionPlan


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
