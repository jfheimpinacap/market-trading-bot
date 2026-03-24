from decimal import Decimal

from rest_framework import serializers

from apps.markets.models import Market
from apps.paper_trading.models import (
    PaperAccount,
    PaperPortfolioSnapshot,
    PaperPosition,
    PaperPositionSide,
    PaperPositionStatus,
    PaperTrade,
    PaperTradeType,
)
from apps.paper_trading.services.execution import execute_paper_trade
from apps.paper_trading.services.portfolio import build_account_summary, get_active_account
from apps.paper_trading.services.valuation import PaperTradingError


class PaperAccountSerializer(serializers.ModelSerializer):
    open_positions_count = serializers.SerializerMethodField()

    class Meta:
        model = PaperAccount
        fields = (
            'id',
            'name',
            'slug',
            'currency',
            'initial_balance',
            'cash_balance',
            'reserved_balance',
            'equity',
            'realized_pnl',
            'unrealized_pnl',
            'total_pnl',
            'is_active',
            'notes',
            'open_positions_count',
            'created_at',
            'updated_at',
        )

    def get_open_positions_count(self, obj):
        return obj.positions.filter(status=PaperPositionStatus.OPEN, quantity__gt=0).count()


class PaperPositionSerializer(serializers.ModelSerializer):
    market_title = serializers.CharField(source='market.title', read_only=True)
    market_slug = serializers.CharField(source='market.slug', read_only=True)
    market_status = serializers.CharField(source='market.status', read_only=True)
    market_source_type = serializers.CharField(source='market.source_type', read_only=True)
    is_real_data = serializers.SerializerMethodField()
    execution_mode = serializers.SerializerMethodField()

    class Meta:
        model = PaperPosition
        fields = (
            'id',
            'account',
            'market',
            'market_title',
            'market_slug',
            'market_status',
            'market_source_type',
            'is_real_data',
            'execution_mode',
            'side',
            'quantity',
            'average_entry_price',
            'current_mark_price',
            'cost_basis',
            'market_value',
            'realized_pnl',
            'unrealized_pnl',
            'status',
            'opened_at',
            'closed_at',
            'last_marked_at',
            'metadata',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields

    def get_is_real_data(self, obj):
        return obj.market.source_type == 'real_read_only'

    def get_execution_mode(self, obj):
        return 'paper_demo_only'


class PaperTradeSerializer(serializers.ModelSerializer):
    market_title = serializers.CharField(source='market.title', read_only=True)
    market_source_type = serializers.CharField(source='market.source_type', read_only=True)
    is_real_data = serializers.SerializerMethodField()
    execution_mode = serializers.SerializerMethodField()

    class Meta:
        model = PaperTrade
        fields = (
            'id',
            'account',
            'market',
            'market_title',
            'market_source_type',
            'is_real_data',
            'execution_mode',
            'position',
            'trade_type',
            'side',
            'quantity',
            'price',
            'gross_amount',
            'fees',
            'status',
            'executed_at',
            'notes',
            'metadata',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields

    def get_is_real_data(self, obj):
        return obj.market.source_type == 'real_read_only'

    def get_execution_mode(self, obj):
        return 'paper_demo_only'


class PaperPortfolioSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaperPortfolioSnapshot
        fields = (
            'id',
            'account',
            'captured_at',
            'cash_balance',
            'equity',
            'realized_pnl',
            'unrealized_pnl',
            'total_pnl',
            'open_positions_count',
            'metadata',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class PaperTradeCreateSerializer(serializers.Serializer):
    market_id = serializers.PrimaryKeyRelatedField(queryset=Market.objects.all(), source='market')
    trade_type = serializers.ChoiceField(choices=PaperTradeType.choices)
    side = serializers.ChoiceField(choices=PaperPositionSide.choices)
    quantity = serializers.DecimalField(max_digits=14, decimal_places=4, min_value=Decimal('0.0001'))
    notes = serializers.CharField(required=False, allow_blank=True)
    metadata = serializers.JSONField(required=False)

    def create(self, validated_data):
        try:
            result = execute_paper_trade(
                market=validated_data['market'],
                trade_type=validated_data['trade_type'],
                side=validated_data['side'],
                quantity=validated_data['quantity'],
                notes=validated_data.get('notes', ''),
                metadata=validated_data.get('metadata') or {},
            )
        except PaperTradingError as exc:
            raise serializers.ValidationError({'detail': str(exc)}) from exc
        return result

    def to_representation(self, instance):
        return {
            'account': PaperAccountSerializer(instance.account).data,
            'position': PaperPositionSerializer(instance.position).data,
            'trade': PaperTradeSerializer(instance.trade).data,
        }


class PaperAccountSummarySerializer(serializers.Serializer):
    account = PaperAccountSerializer()
    open_positions_count = serializers.IntegerField()
    closed_positions_count = serializers.IntegerField()
    exposure_by_market = serializers.ListField(child=serializers.DictField())
    recent_trades = serializers.ListField(child=serializers.DictField())

    @classmethod
    def from_active_account(cls):
        summary = build_account_summary(account=get_active_account())
        return cls(summary)
