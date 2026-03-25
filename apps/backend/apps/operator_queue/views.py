from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.operator_queue.models import OperatorQueueItem
from apps.operator_queue.serializers import OperatorQueueDecisionSerializer, OperatorQueueItemSerializer, OperatorQueueSnoozeSerializer
from apps.operator_queue.services import (
    approve_queue_item,
    build_queue_summary,
    get_queue_queryset,
    rebuild_from_pending_approvals,
    reject_queue_item,
    snooze_queue_item,
)


class OperatorQueueListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = OperatorQueueItemSerializer

    def get_queryset(self):
        queryset = get_queue_queryset().order_by('-created_at', '-id')
        status_filter = self.request.query_params.get('status')
        source = self.request.query_params.get('source')
        queue_type = self.request.query_params.get('queue_type')
        priority = self.request.query_params.get('priority')
        source_type = self.request.query_params.get('source_type')
        is_real_data = self.request.query_params.get('is_real_data')

        if status_filter:
            queryset = queryset.filter(status=status_filter.upper())
        if source:
            queryset = queryset.filter(source=source)
        if queue_type:
            queryset = queryset.filter(queue_type=queue_type)
        if priority:
            queryset = queryset.filter(priority=priority)
        if source_type:
            queryset = queryset.filter(related_market__source_type=source_type.upper())
        if is_real_data is not None:
            truthy = is_real_data.lower() in {'1', 'true', 'yes'}
            queryset = queryset.filter(related_market__source_type='REAL_READ_ONLY' if truthy else 'DEMO')

        return queryset[:100]


class OperatorQueueDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = OperatorQueueItemSerializer
    queryset = OperatorQueueItem.objects.select_related('related_market', 'related_proposal', 'related_pending_approval', 'related_trade').prefetch_related('decision_logs')


class OperatorQueueSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(build_queue_summary(), status=status.HTTP_200_OK)


class OperatorQueueApproveView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, pk, *args, **kwargs):
        serializer = OperatorQueueDecisionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        item = get_object_or_404(OperatorQueueItem, pk=pk)
        item = approve_queue_item(item=item, decision_note=serializer.validated_data.get('decision_note', ''), decided_by=serializer.validated_data.get('decided_by', 'local-operator'))
        return Response(OperatorQueueItemSerializer(item).data, status=status.HTTP_200_OK)


class OperatorQueueRejectView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, pk, *args, **kwargs):
        serializer = OperatorQueueDecisionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        item = get_object_or_404(OperatorQueueItem, pk=pk)
        item = reject_queue_item(item=item, decision_note=serializer.validated_data.get('decision_note', ''), decided_by=serializer.validated_data.get('decided_by', 'local-operator'))
        return Response(OperatorQueueItemSerializer(item).data, status=status.HTTP_200_OK)


class OperatorQueueSnoozeView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, pk, *args, **kwargs):
        serializer = OperatorQueueSnoozeSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        item = get_object_or_404(OperatorQueueItem, pk=pk)
        item = snooze_queue_item(
            item=item,
            decision_note=serializer.validated_data.get('decision_note', ''),
            snooze_until=serializer.validated_data.get('snooze_until'),
            snooze_hours=serializer.validated_data.get('snooze_hours', 6),
            decided_by=serializer.validated_data.get('decided_by', 'local-operator'),
        )
        return Response(OperatorQueueItemSerializer(item).data, status=status.HTTP_200_OK)


class OperatorQueueRebuildView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        created = rebuild_from_pending_approvals()
        return Response({'created': created}, status=status.HTTP_200_OK)
