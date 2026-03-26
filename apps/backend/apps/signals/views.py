from django.db.models import Count, Max
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.signals.models import MarketSignal, MarketSignalStatus, MockAgent, OpportunitySignal, SignalDirection, SignalFusionRun, SignalRun
from apps.signals.serializers import (
    MarketSignalDetailSerializer,
    MarketSignalListSerializer,
    MockAgentSerializer,
    OpportunitySignalSerializer,
    RunFusionRequestSerializer,
    RunToProposalRequestSerializer,
    SignalBoardSummarySerializer,
    SignalFusionRunSerializer,
    SignalRunSerializer,
    SignalSummarySerializer,
)
from apps.signals.services import get_board_summary, run_fusion_to_proposal, run_signal_fusion


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


class RunSignalFusionView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RunFusionRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        run = run_signal_fusion(
            profile_slug=serializer.validated_data.get('profile_slug'),
            market_ids=serializer.validated_data.get('market_ids'),
            triggered_by='manual_api',
        )
        return Response(SignalFusionRunSerializer(run).data, status=status.HTTP_201_CREATED)


class SignalFusionRunListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = SignalFusionRunSerializer

    def get_queryset(self):
        return SignalFusionRun.objects.order_by('-created_at', '-id')[:50]


class SignalFusionRunDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = SignalFusionRunSerializer

    def get_queryset(self):
        return SignalFusionRun.objects.order_by('-created_at', '-id')


class OpportunitySignalListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = OpportunitySignalSerializer

    def get_queryset(self):
        queryset = OpportunitySignal.objects.select_related('market', 'market__provider', 'run', 'proposal_gate').order_by('rank', '-opportunity_score', '-id')
        run_id = self.request.query_params.get('run_id')
        status_filter = self.request.query_params.get('status')
        if run_id:
            queryset = queryset.filter(run_id=run_id)
        if status_filter:
            queryset = queryset.filter(opportunity_status=status_filter)
        return queryset[:300]


class SignalBoardSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        payload = get_board_summary()
        serializer = SignalBoardSummarySerializer(
            {
                **payload,
                'latest_run': SignalFusionRunSerializer(payload['latest_run']).data if payload['latest_run'] else None,
            }
        )
        return Response(serializer.data)


class RunFusionToProposalView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RunToProposalRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        run = SignalFusionRun.objects.filter(id=serializer.validated_data['run_id']).first()
        if not run:
            return Response({'detail': 'Signal fusion run not found.'}, status=status.HTTP_404_NOT_FOUND)
        proposals = run_fusion_to_proposal(run=run, min_priority=serializer.validated_data['min_priority'])
        return Response({'run_id': run.id, 'proposals_created': len(proposals)}, status=status.HTTP_201_CREATED)
