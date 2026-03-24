from rest_framework import serializers

from apps.markets.models import Market
from apps.paper_trading.models import PaperAccount
from apps.proposal_engine.models import TradeProposal
from apps.proposal_engine.services import generate_trade_proposal


class TradeProposalSerializer(serializers.ModelSerializer):
    market_title = serializers.CharField(source='market.title', read_only=True)
    market_slug = serializers.CharField(source='market.slug', read_only=True)
    market_source_type = serializers.CharField(source='market.source_type', read_only=True)
    is_real_data = serializers.SerializerMethodField()
    execution_mode = serializers.SerializerMethodField()
    paper_account_slug = serializers.CharField(source='paper_account.slug', read_only=True)

    class Meta:
        model = TradeProposal
        fields = (
            'id',
            'market',
            'market_title',
            'market_slug',
            'market_source_type',
            'is_real_data',
            'execution_mode',
            'paper_account',
            'paper_account_slug',
            'proposal_status',
            'direction',
            'proposal_score',
            'confidence',
            'headline',
            'thesis',
            'rationale',
            'suggested_trade_type',
            'suggested_side',
            'suggested_quantity',
            'suggested_price_reference',
            'risk_decision',
            'policy_decision',
            'approval_required',
            'is_actionable',
            'recommendation',
            'expires_at',
            'metadata',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields

    def get_is_real_data(self, obj):
        return obj.market.source_type == 'real_read_only'

    def get_execution_mode(self, obj):
        return 'paper_demo_only'


class GenerateTradeProposalRequestSerializer(serializers.Serializer):
    market_id = serializers.PrimaryKeyRelatedField(queryset=Market.objects.all(), source='market')
    paper_account_id = serializers.PrimaryKeyRelatedField(
        queryset=PaperAccount.objects.all(),
        source='paper_account',
        required=False,
        allow_null=True,
    )
    triggered_from = serializers.ChoiceField(
        choices=['market_detail', 'signals', 'dashboard', 'automation'],
        required=False,
        default='market_detail',
    )

    def create(self, validated_data):
        return generate_trade_proposal(
            market=validated_data['market'],
            paper_account=validated_data.get('paper_account'),
            triggered_from=validated_data.get('triggered_from', 'market_detail'),
        )


class GenerateTradeProposalSerializer(GenerateTradeProposalRequestSerializer):
    def to_representation(self, instance):
        return {'proposal': TradeProposalSerializer(instance).data}
