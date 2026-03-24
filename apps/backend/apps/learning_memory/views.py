from decimal import Decimal

from django.db.models import Count
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.learning_memory.models import LearningAdjustment, LearningMemoryEntry, LearningOutcome
from apps.learning_memory.serializers import LearningAdjustmentSerializer, LearningMemoryEntrySerializer, LearningSummarySerializer
from apps.learning_memory.services import (
    ingest_recent_evaluation_runs,
    ingest_recent_reviews,
    ingest_recent_safety_events,
    rebuild_active_adjustments,
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
        created_reviews = ingest_recent_reviews()
        created_eval = ingest_recent_evaluation_runs()
        created_safety = ingest_recent_safety_events()
        adjusted = rebuild_active_adjustments()
        return Response(
            {
                'status': 'ok',
                'created_memory_entries': created_reviews + created_eval + created_safety,
                'created_from_reviews': created_reviews,
                'created_from_evaluation': created_eval,
                'created_from_safety': created_safety,
                **adjusted,
            },
            status=status.HTTP_200_OK,
        )
