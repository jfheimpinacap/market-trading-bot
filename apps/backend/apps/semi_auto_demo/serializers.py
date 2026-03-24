from rest_framework import serializers

from apps.paper_trading.serializers import PaperTradeSerializer
from apps.semi_auto_demo.models import PendingApproval, SemiAutoRun


class SemiAutoRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = SemiAutoRun
        fields = (
            'id',
            'run_type',
            'status',
            'started_at',
            'finished_at',
            'markets_evaluated',
            'proposals_generated',
            'auto_executed_count',
            'approval_required_count',
            'blocked_count',
            'summary',
            'details',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class PendingApprovalSerializer(serializers.ModelSerializer):
    market_title = serializers.CharField(source='market.title', read_only=True)
    proposal_headline = serializers.CharField(source='proposal.headline', read_only=True)
    proposal_thesis = serializers.CharField(source='proposal.thesis', read_only=True)
    executed_trade = PaperTradeSerializer(read_only=True)

    class Meta:
        model = PendingApproval
        fields = (
            'id',
            'proposal',
            'proposal_headline',
            'proposal_thesis',
            'market',
            'market_title',
            'paper_account',
            'status',
            'requested_action',
            'suggested_side',
            'suggested_quantity',
            'policy_decision',
            'summary',
            'rationale',
            'decided_at',
            'decision_note',
            'metadata',
            'executed_trade',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class PendingApprovalDecisionSerializer(serializers.Serializer):
    decision_note = serializers.CharField(required=False, allow_blank=True, max_length=500)
