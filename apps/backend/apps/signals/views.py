from django.db.models import Count, Max
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.signals.models import MarketSignal, MarketSignalStatus, MockAgent, SignalDirection, SignalRun
from apps.signals.serializers import (
    MarketSignalDetailSerializer,
    MarketSignalListSerializer,
    MockAgentSerializer,
    SignalRunSerializer,
    SignalSummarySerializer,
)


class MockAgentListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = MockAgentSerializer

    def get_queryset(self):
        return MockAgent.objects.annotate(signal_count=Count('signals')).order_by('name')


class MarketSignalListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = MarketSignalListSerializer
    ordering_fields = ('created_at', 'score', 'confidence')

    def get_queryset(self):
        queryset = MarketSignal.objects.select_related('market', 'market__provider', 'agent', 'run')

        market = self.request.query_params.get('market')
        if market:
            queryset = queryset.filter(market_id=market)

        agent = self.request.query_params.get('agent')
        if agent:
            if agent.isdigit():
                queryset = queryset.filter(agent_id=agent)
            else:
                queryset = queryset.filter(agent__slug=agent)

        signal_type = self.request.query_params.get('signal_type')
        if signal_type:
            queryset = queryset.filter(signal_type=signal_type)

        status_value = self.request.query_params.get('status')
        if status_value:
            queryset = queryset.filter(status=status_value)

        direction = self.request.query_params.get('direction')
        if direction:
            queryset = queryset.filter(direction=direction)

        is_actionable = self.request.query_params.get('is_actionable')
        if is_actionable is not None:
            normalized = is_actionable.strip().lower()
            if normalized in {'1', 'true', 'yes'}:
                queryset = queryset.filter(is_actionable=True)
            elif normalized in {'0', 'false', 'no'}:
                queryset = queryset.filter(is_actionable=False)

        ordering = self.request.query_params.get('ordering')
        if ordering:
            requested_fields = [field.strip() for field in ordering.split(',') if field.strip()]
            valid_fields = []
            for field in requested_fields:
                raw_field = field[1:] if field.startswith('-') else field
                if raw_field in self.ordering_fields:
                    valid_fields.append(field)
            if valid_fields:
                return queryset.order_by(*valid_fields)

        return queryset.order_by('-created_at', '-id')


class MarketSignalDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = MarketSignalDetailSerializer

    def get_queryset(self):
        return MarketSignal.objects.select_related('market', 'market__provider', 'agent', 'run')


class SignalSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        queryset = MarketSignal.objects.all()
        latest_run = SignalRun.objects.order_by('-started_at', '-id').first()
        payload = {
            'total_signals': queryset.count(),
            'active_signals': queryset.filter(status__in=[MarketSignalStatus.ACTIVE, MarketSignalStatus.MONITOR]).count(),
            'actionable_signals': queryset.filter(is_actionable=True).count(),
            'bullish_signals': queryset.filter(direction=SignalDirection.BULLISH).count(),
            'bearish_signals': queryset.filter(direction=SignalDirection.BEARISH).count(),
            'neutral_signals': queryset.filter(direction=SignalDirection.NEUTRAL).count(),
            'active_agents': MockAgent.objects.filter(is_active=True).count(),
            'markets_with_signals': queryset.values('market_id').distinct().count(),
            'latest_signal_at': queryset.aggregate(latest=Max('created_at'))['latest'],
            'latest_run': SignalRunSerializer(latest_run).data if latest_run else None,
        }
        serializer = SignalSummarySerializer(payload)
        return Response(serializer.data)
