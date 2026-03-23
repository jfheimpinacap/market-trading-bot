from rest_framework import serializers

from apps.postmortem_demo.models import TradeReview


class TradeReviewListSerializer(serializers.ModelSerializer):
    trade_id = serializers.IntegerField(source='paper_trade_id', read_only=True)
    trade_type = serializers.CharField(source='paper_trade.trade_type', read_only=True)
    trade_side = serializers.CharField(source='paper_trade.side', read_only=True)
    trade_quantity = serializers.DecimalField(source='paper_trade.quantity', read_only=True, max_digits=14, decimal_places=4)
    trade_executed_at = serializers.DateTimeField(source='paper_trade.executed_at', read_only=True)
    paper_account_slug = serializers.CharField(source='paper_account.slug', read_only=True)
    paper_account_name = serializers.CharField(source='paper_account.name', read_only=True)
    market_title = serializers.CharField(source='market.title', read_only=True)
    market_slug = serializers.CharField(source='market.slug', read_only=True)
    market_status = serializers.CharField(source='market.status', read_only=True)

    class Meta:
        model = TradeReview
        fields = (
            'id',
            'paper_trade',
            'trade_id',
            'trade_type',
            'trade_side',
            'trade_quantity',
            'trade_executed_at',
            'paper_account',
            'paper_account_slug',
            'paper_account_name',
            'market',
            'market_title',
            'market_slug',
            'market_status',
            'review_status',
            'outcome',
            'score',
            'confidence',
            'summary',
            'lesson',
            'recommendation',
            'entry_price',
            'current_market_price',
            'price_delta',
            'pnl_estimate',
            'market_probability_at_trade',
            'market_probability_now',
            'risk_decision_at_trade',
            'reviewed_at',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class TradeReviewDetailSerializer(TradeReviewListSerializer):
    rationale = serializers.CharField(read_only=True)
    signals_context = serializers.JSONField(read_only=True)
    trade_notes = serializers.CharField(source='paper_trade.notes', read_only=True)
    trade_metadata = serializers.JSONField(source='paper_trade.metadata', read_only=True)
    metadata = serializers.JSONField(read_only=True)

    class Meta(TradeReviewListSerializer.Meta):
        fields = TradeReviewListSerializer.Meta.fields + (
            'rationale',
            'signals_context',
            'trade_notes',
            'trade_metadata',
            'metadata',
        )


class TradeReviewSummarySerializer(serializers.Serializer):
    total_reviews = serializers.IntegerField()
    reviewed_reviews = serializers.IntegerField()
    stale_reviews = serializers.IntegerField()
    favorable_reviews = serializers.IntegerField()
    neutral_reviews = serializers.IntegerField()
    unfavorable_reviews = serializers.IntegerField()
    average_score = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)
    latest_reviewed_at = serializers.DateTimeField(allow_null=True)
