from rest_framework import generics, status
from rest_framework.response import Response

from apps.proposal_engine.models import TradeProposal
from apps.proposal_engine.serializers import (
    GenerateTradeProposalSerializer,
    TradeProposalSerializer,
)


class TradeProposalListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = TradeProposalSerializer

    def get_queryset(self):
        queryset = TradeProposal.objects.select_related('market', 'paper_account').order_by('-created_at', '-id')
        market = self.request.query_params.get('market')
        if market:
            queryset = queryset.filter(market_id=market)
        direction = self.request.query_params.get('direction')
        if direction:
            queryset = queryset.filter(direction=direction.upper())
        actionable = self.request.query_params.get('is_actionable')
        if actionable is not None:
            normalized = actionable.strip().lower()
            if normalized in {'1', 'true', 'yes'}:
                queryset = queryset.filter(is_actionable=True)
            elif normalized in {'0', 'false', 'no'}:
                queryset = queryset.filter(is_actionable=False)
        return queryset[:50]


class TradeProposalDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = TradeProposalSerializer

    def get_queryset(self):
        return TradeProposal.objects.select_related('market', 'paper_account')


class GenerateTradeProposalView(generics.GenericAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = GenerateTradeProposalSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        proposal = serializer.save()
        return Response(serializer.to_representation(proposal), status=status.HTTP_201_CREATED)
