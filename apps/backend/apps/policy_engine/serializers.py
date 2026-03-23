from decimal import Decimal

from rest_framework import serializers

from apps.markets.models import Market
from apps.paper_trading.models import PaperPositionSide, PaperTradeType
from apps.policy_engine.models import (
    ApprovalDecision,
    PolicyRequestedBy,
    PolicyTriggeredFrom,
)
from apps.policy_engine.services import PolicyEvaluationError, evaluate_trade_policy
from apps.risk_demo.models import TradeRiskAssessment


class PolicyMatchedRuleSerializer(serializers.Serializer):
    code = serializers.CharField()
    title = serializers.CharField()
    outcome = serializers.CharField()
    severity = serializers.CharField()
    message = serializers.CharField()
    recommendation = serializers.CharField(allow_blank=True)


class ApprovalDecisionSerializer(serializers.ModelSerializer):
    market_title = serializers.CharField(source='market.title', read_only=True)
    market_slug = serializers.CharField(source='market.slug', read_only=True)
    paper_account_slug = serializers.CharField(source='paper_account.slug', read_only=True)
    linked_signal_id = serializers.IntegerField(source='linked_signal.id', read_only=True, allow_null=True)
    matched_rules = PolicyMatchedRuleSerializer(many=True, read_only=True)

    class Meta:
        model = ApprovalDecision
        fields = (
            'id',
            'market',
            'market_title',
            'market_slug',
            'paper_account',
            'paper_account_slug',
            'risk_assessment',
            'linked_signal_id',
            'trade_type',
            'side',
            'quantity',
            'requested_price',
            'estimated_gross_amount',
            'requested_by',
            'triggered_from',
            'decision',
            'severity',
            'confidence',
            'summary',
            'rationale',
            'matched_rules',
            'recommendation',
            'risk_decision',
            'metadata',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class EvaluateTradePolicyRequestSerializer(serializers.Serializer):
    market_id = serializers.PrimaryKeyRelatedField(queryset=Market.objects.all(), source='market')
    trade_type = serializers.ChoiceField(choices=PaperTradeType.choices)
    side = serializers.ChoiceField(choices=PaperPositionSide.choices)
    quantity = serializers.DecimalField(max_digits=14, decimal_places=4, min_value=Decimal('0.0001'))
    requested_price = serializers.DecimalField(max_digits=12, decimal_places=4, required=False, allow_null=True)
    triggered_from = serializers.ChoiceField(choices=PolicyTriggeredFrom.choices, required=False, default=PolicyTriggeredFrom.MARKET_DETAIL)
    requested_by = serializers.ChoiceField(choices=PolicyRequestedBy.choices, required=False, default=PolicyRequestedBy.USER)
    risk_assessment_id = serializers.PrimaryKeyRelatedField(
        queryset=TradeRiskAssessment.objects.all(),
        source='risk_assessment',
        required=False,
        allow_null=True,
    )
    metadata = serializers.JSONField(required=False)

    def create(self, validated_data):
        try:
            return evaluate_trade_policy(
                market=validated_data['market'],
                trade_type=validated_data['trade_type'],
                side=validated_data['side'],
                quantity=validated_data['quantity'],
                requested_price=validated_data.get('requested_price'),
                triggered_from=validated_data.get('triggered_from', PolicyTriggeredFrom.MARKET_DETAIL),
                requested_by=validated_data.get('requested_by', PolicyRequestedBy.USER),
                risk_assessment=validated_data.get('risk_assessment'),
                metadata=validated_data.get('metadata') or {},
            )
        except PolicyEvaluationError as exc:
            raise serializers.ValidationError({'detail': str(exc)}) from exc

    def to_representation(self, instance):
        return ApprovalDecisionSerializer(instance).data


class PolicyDecisionSummarySerializer(serializers.Serializer):
    total_decisions = serializers.IntegerField()
    auto_approve_count = serializers.IntegerField()
    approval_required_count = serializers.IntegerField()
    hard_block_count = serializers.IntegerField()
    latest_decision = ApprovalDecisionSerializer(allow_null=True)
