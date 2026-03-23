from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.paper_trading.models import PaperPortfolioSnapshot, PaperPosition, PaperTrade
from apps.paper_trading.serializers import (
    PaperAccountSerializer,
    PaperAccountSummarySerializer,
    PaperPortfolioSnapshotSerializer,
    PaperPositionSerializer,
    PaperTradeCreateSerializer,
    PaperTradeSerializer,
)
from apps.paper_trading.services.portfolio import get_active_account
from apps.paper_trading.services.valuation import revalue_account


class PaperAccountView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        account = get_active_account()
        revalue_account(account)
        return Response(PaperAccountSerializer(account).data)


class PaperPositionListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PaperPositionSerializer

    def get_queryset(self):
        account = get_active_account()
        queryset = PaperPosition.objects.filter(account=account).select_related('market', 'account')
        status_value = self.request.query_params.get('status')
        if status_value:
            queryset = queryset.filter(status=status_value.upper())
        return queryset.order_by('-market_value', '-updated_at')


class PaperTradeListCreateView(generics.ListCreateAPIView):
    authentication_classes = []
    permission_classes = []

    def get_queryset(self):
        account = get_active_account()
        return PaperTrade.objects.filter(account=account).select_related('market', 'position', 'account').order_by('-executed_at', '-id')

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return PaperTradeCreateSerializer
        return PaperTradeSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(serializer.to_representation(result), status=status.HTTP_201_CREATED)


class PaperSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        serializer = PaperAccountSummarySerializer.from_active_account()
        return Response(serializer.data)


class PaperRevalueView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        account = get_active_account()
        revalue_account(account, create_snapshot=True)
        return Response(PaperAccountSerializer(account).data)


class PaperPortfolioSnapshotListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PaperPortfolioSnapshotSerializer

    def get_queryset(self):
        account = get_active_account()
        return PaperPortfolioSnapshot.objects.filter(account=account).select_related('account').order_by('-captured_at', '-id')[:50]
