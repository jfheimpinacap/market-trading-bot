from decimal import Decimal

from rest_framework import serializers

from apps.allocation_engine.models import AllocationDecision, AllocationRun


class AllocationDecisionSerializer(serializers.ModelSerializer):
    proposal_headline = serializers.CharField(source='proposal.headline', read_only=True)
    market_title = serializers.CharField(source='proposal.market.title', read_only=True)
    direction = serializers.CharField(source='proposal.direction', read_only=True)
    proposal_score = serializers.DecimalField(source='proposal.proposal_score', max_digits=5, decimal_places=2, read_only=True)
    confidence = serializers.DecimalField(source='proposal.confidence', max_digits=5, decimal_places=2, read_only=True)
    suggested_quantity = serializers.DecimalField(source='proposal.suggested_quantity', max_digits=14, decimal_places=4, read_only=True)
    source_type = serializers.CharField(source='proposal.market.source_type', read_only=True)
    provider = serializers.CharField(source='proposal.market.provider.slug', read_only=True)

    class Meta:
        model = AllocationDecision
        fields = (
            'id',
            'proposal',
            'proposal_headline',
            'market_title',
            'direction',
            'proposal_score',
            'confidence',
            'suggested_quantity',
            'source_type',
            'provider',
            'rank',
            'final_allocated_quantity',
            'decision',
            'rationale',
            'details',
            'created_at',
        )
        read_only_fields = fields


class AllocationRunSerializer(serializers.ModelSerializer):
    decisions = AllocationDecisionSerializer(many=True, read_only=True)

    class Meta:
        model = AllocationRun
        fields = (
            'id',
            'status',
            'scope_type',
            'triggered_from',
            'started_at',
            'finished_at',
            'proposals_considered',
            'proposals_ranked',
            'proposals_selected',
            'proposals_rejected',
            'allocated_total',
            'remaining_cash',
            'summary',
            'details',
            'decisions',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class AllocationEvaluateRequestSerializer(serializers.Serializer):
    scope_type = serializers.ChoiceField(choices=['real_only', 'demo_only', 'mixed'], required=False, default='mixed')
    max_candidates = serializers.IntegerField(min_value=1, required=False)
    max_executions = serializers.IntegerField(min_value=1, required=False)
    triggered_from = serializers.CharField(required=False, default='manual')


class AllocationSummarySerializer(serializers.Serializer):
    total_runs = serializers.IntegerField()
    latest_run = AllocationRunSerializer(allow_null=True)
    selected_total = serializers.IntegerField()
    rejected_total = serializers.IntegerField()
    allocated_total = serializers.DecimalField(max_digits=14, decimal_places=2)


class AllocationEvaluateResponseSerializer(serializers.Serializer):
    scope_type = serializers.CharField()
    triggered_from = serializers.CharField()
    proposals_considered = serializers.IntegerField()
    proposals_ranked = serializers.IntegerField()
    proposals_selected = serializers.IntegerField()
    proposals_rejected = serializers.IntegerField()
    allocated_total = serializers.DecimalField(max_digits=14, decimal_places=2)
    remaining_cash = serializers.DecimalField(max_digits=14, decimal_places=2)
    summary = serializers.CharField()
    details = serializers.JSONField()
    run_id = serializers.IntegerField(allow_null=True)

    def to_representation(self, instance):
        base = super().to_representation(instance)
        base['allocated_total'] = str(Decimal(base['allocated_total']).quantize(Decimal('0.01')))
        base['remaining_cash'] = str(Decimal(base['remaining_cash']).quantize(Decimal('0.01')))
        return base
