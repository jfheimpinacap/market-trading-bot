from decimal import Decimal

from django.db.models import Count
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.continuous_demo.services.control import DEFAULT_LOOP_SETTINGS
from apps.learning_memory.models import LearningAdjustment, LearningMemoryEntry, LearningOutcome, LearningRebuildRun
from apps.learning_memory.serializers import (
    LearningAdjustmentSerializer,
    LearningMemoryEntrySerializer,
    LearningRebuildRequestSerializer,
    LearningRebuildRunSerializer,
    LearningSummarySerializer,
)
from apps.learning_memory.services import (
    run_learning_rebuild,
)


class LearningMemoryListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = LearningMemoryEntrySerializer

    def get_queryset(self):
        queryset = LearningMemoryEntry.objects.select_related('provider', 'market', 'related_signal').order_by('-created_at', '-id')
        outcome = self.request.query_params.get('outcome')
        memory_type = self.request.query_params.get('memory_type')
        if outcome:
            queryset = queryset.filter(outcome=outcome)
        if memory_type:
            queryset = queryset.filter(memory_type=memory_type)
        return queryset[:100]


class LearningMemoryDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = LearningMemoryEntrySerializer

    def get_queryset(self):
        return LearningMemoryEntry.objects.select_related('provider', 'market', 'related_signal').order_by('-created_at', '-id')


class LearningAdjustmentListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = LearningAdjustmentSerializer

    def get_queryset(self):
        queryset = LearningAdjustment.objects.order_by('-updated_at', '-id')
        active = self.request.query_params.get('is_active')
        if active is not None:
            norm = active.strip().lower()
            if norm in {'1', 'true', 'yes'}:
                queryset = queryset.filter(is_active=True)
            elif norm in {'0', 'false', 'no'}:
                queryset = queryset.filter(is_active=False)
        return queryset[:100]


class LearningSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        entries = LearningMemoryEntry.objects.all()
        adjustments = LearningAdjustment.objects.all()

        entries_by_outcome = {item['outcome']: item['total'] for item in entries.values('outcome').annotate(total=Count('id'))}
        adjustments_by_scope = {item['scope_type']: item['total'] for item in adjustments.filter(is_active=True).values('scope_type').annotate(total=Count('id'))}

        active_adjustments = adjustments.filter(is_active=True)
        conservative_bias_score = sum((abs(item.magnitude) for item in active_adjustments), Decimal('0.0000')).quantize(Decimal('0.0001'))

        payload = {
            'total_memory_entries': entries.count(),
            'active_adjustments': active_adjustments.count(),
            'negative_patterns_detected': entries.filter(outcome=LearningOutcome.NEGATIVE).count(),
            'conservative_bias_score': conservative_bias_score,
            'entries_by_outcome': entries_by_outcome,
            'adjustments_by_scope': adjustments_by_scope,
            'recent_memory': entries.order_by('-created_at', '-id')[:10],
            'recent_adjustments': active_adjustments.order_by('-updated_at', '-id')[:10],
        }
        return Response(LearningSummarySerializer(payload).data, status=status.HTTP_200_OK)


class LearningRebuildView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = LearningRebuildRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        rebuild_run = run_learning_rebuild(
            triggered_from=serializer.validated_data['triggered_from'],
            related_session_id=serializer.validated_data.get('related_session_id'),
            related_cycle_id=serializer.validated_data.get('related_cycle_id'),
        )
        return Response(LearningRebuildRunSerializer(rebuild_run).data, status=status.HTTP_200_OK)


class LearningRebuildRunListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = LearningRebuildRunSerializer

    def get_queryset(self):
        return LearningRebuildRun.objects.order_by('-started_at', '-id')[:100]


class LearningRebuildRunDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = LearningRebuildRunSerializer
    queryset = LearningRebuildRun.objects.order_by('-started_at', '-id')


class LearningIntegrationStatusView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        latest = LearningRebuildRun.objects.order_by('-started_at', '-id').first()
        return Response(
            {
                'learning_rebuild_enabled': DEFAULT_LOOP_SETTINGS.get('learning_rebuild_enabled', False),
                'learning_rebuild_every_n_cycles': DEFAULT_LOOP_SETTINGS.get('learning_rebuild_every_n_cycles'),
                'learning_rebuild_after_reviews': DEFAULT_LOOP_SETTINGS.get('learning_rebuild_after_reviews', False),
                'latest_rebuild_run': LearningRebuildRunSerializer(latest).data if latest else None,
                'message': (
                    'Learning rebuild is currently manual.'
                    if not DEFAULT_LOOP_SETTINGS.get('learning_rebuild_enabled', False)
                    else 'Automatic rebuild can run with conservative cadence.'
                ),
            },
            status=status.HTTP_200_OK,
        )
