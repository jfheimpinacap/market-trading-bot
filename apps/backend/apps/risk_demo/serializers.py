from decimal import Decimal

from rest_framework import serializers

from apps.markets.models import Market
from apps.paper_trading.models import PaperPositionSide, PaperTradeType
from apps.risk_demo.models import TradeRiskAssessment
from apps.risk_demo.services.assessment import assess_trade


class TradeRiskAssessmentSerializer(serializers.ModelSerializer):
    market_title = serializers.CharField(source='market.title', read_only=True)
    market_slug = serializers.CharField(source='market.slug', read_only=True)
    paper_account_slug = serializers.CharField(source='paper_account.slug', read_only=True)

    class Meta:
        model = TradeRiskAssessment
        fields = (
            'id',
            'market',
            'market_title',
            'market_slug',
            'paper_account',
            'paper_account_slug',
            'side',
            'trade_type',
            'quantity',
            'requested_price',
            'current_market_probability',
            'current_yes_price',
            'current_no_price',
            'decision',
            'score',
            'confidence',
            'summary',
            'rationale',
            'warnings',
            'suggested_quantity',
            'is_actionable',
            'metadata',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class AssessTradeRequestSerializer(serializers.Serializer):
    market_id = serializers.PrimaryKeyRelatedField(queryset=Market.objects.all(), source='market')
    trade_type = serializers.ChoiceField(choices=PaperTradeType.choices)
    side = serializers.ChoiceField(choices=PaperPositionSide.choices)
    quantity = serializers.DecimalField(max_digits=14, decimal_places=4, min_value=Decimal('0.0001'))
    requested_price = serializers.DecimalField(max_digits=12, decimal_places=4, required=False, allow_null=True)
    metadata = serializers.JSONField(required=False)


class AssessTradeResponseSerializer(serializers.Serializer):
    assessment = TradeRiskAssessmentSerializer(read_only=True)


class AssessTradeSerializer(AssessTradeRequestSerializer):
    def create(self, validated_data):
        return assess_trade(
            market=validated_data['market'],
            trade_type=validated_data['trade_type'],
            side=validated_data['side'],
            quantity=validated_data['quantity'],
            requested_price=validated_data.get('requested_price'),
            metadata=validated_data.get('metadata') or {},
        )

    def to_representation(self, instance):
        return {'assessment': TradeRiskAssessmentSerializer(instance).data}
