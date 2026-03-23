from rest_framework import generics, status
from rest_framework.response import Response

from apps.risk_demo.models import TradeRiskAssessment
from apps.risk_demo.serializers import AssessTradeSerializer, TradeRiskAssessmentSerializer


class AssessTradeView(generics.GenericAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = AssessTradeSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assessment = serializer.save()
        return Response(serializer.to_representation(assessment), status=status.HTTP_201_CREATED)


class TradeRiskAssessmentListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = TradeRiskAssessmentSerializer

    def get_queryset(self):
        queryset = TradeRiskAssessment.objects.select_related('market', 'paper_account').order_by('-created_at', '-id')
        market = self.request.query_params.get('market')
        if market:
            queryset = queryset.filter(market_id=market)
        decision = self.request.query_params.get('decision')
        if decision:
            queryset = queryset.filter(decision=decision.upper())
        return queryset[:25]
