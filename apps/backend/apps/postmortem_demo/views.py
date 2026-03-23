from django.db.models import Avg, Max
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.postmortem_demo.models import TradeReview, TradeReviewOutcome, TradeReviewStatus
from apps.postmortem_demo.serializers import (
    TradeReviewDetailSerializer,
    TradeReviewListSerializer,
    TradeReviewSummarySerializer,
)


class TradeReviewListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = TradeReviewListSerializer
    ordering_fields = ('reviewed_at', 'score', 'created_at')

    def get_queryset(self):
        queryset = TradeReview.objects.select_related('paper_trade', 'paper_account', 'market', 'market__provider')

        trade = self.request.query_params.get('trade') or self.request.query_params.get('paper_trade')
        if trade:
            queryset = queryset.filter(paper_trade_id=trade)

        market = self.request.query_params.get('market')
        if market:
            queryset = queryset.filter(market_id=market)

        account = self.request.query_params.get('account') or self.request.query_params.get('paper_account')
        if account:
            queryset = queryset.filter(paper_account_id=account)

        outcome = self.request.query_params.get('outcome')
        if outcome:
            queryset = queryset.filter(outcome=outcome.upper())

        review_status = self.request.query_params.get('review_status')
        if review_status:
            queryset = queryset.filter(review_status=review_status.upper())

        ordering = self.request.query_params.get('ordering')
        if ordering:
            valid_fields = []
            for field in [item.strip() for item in ordering.split(',') if item.strip()]:
                raw_field = field[1:] if field.startswith('-') else field
                if raw_field in self.ordering_fields:
                    valid_fields.append(field)
            if valid_fields:
                return queryset.order_by(*valid_fields)

        return queryset.order_by('-reviewed_at', '-id')


class TradeReviewDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = TradeReviewDetailSerializer

    def get_queryset(self):
        return TradeReview.objects.select_related('paper_trade', 'paper_account', 'market', 'market__provider')


class TradeReviewSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        queryset = TradeReview.objects.all()
        payload = {
            'total_reviews': queryset.count(),
            'reviewed_reviews': queryset.filter(review_status=TradeReviewStatus.REVIEWED).count(),
            'stale_reviews': queryset.filter(review_status=TradeReviewStatus.STALE).count(),
            'favorable_reviews': queryset.filter(outcome=TradeReviewOutcome.FAVORABLE).count(),
            'neutral_reviews': queryset.filter(outcome=TradeReviewOutcome.NEUTRAL).count(),
            'unfavorable_reviews': queryset.filter(outcome=TradeReviewOutcome.UNFAVORABLE).count(),
            'average_score': queryset.aggregate(value=Avg('score'))['value'],
            'latest_reviewed_at': queryset.aggregate(value=Max('reviewed_at'))['value'],
        }
        serializer = TradeReviewSummarySerializer(payload)
        return Response(serializer.data)
