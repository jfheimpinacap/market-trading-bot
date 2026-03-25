from django.db.models import Count
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.real_data_sync.models import ProviderSyncRun
from apps.real_data_sync.serializers import (
    ProviderSyncRunSerializer,
    RealSyncRunRequestSerializer,
    RealSyncStatusSerializer,
    RealSyncSummarySerializer,
)
from apps.real_data_sync.services import build_sync_status, run_provider_sync


class RealSyncRunView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RealSyncRunRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        run = run_provider_sync(**serializer.validated_data)
        return Response(ProviderSyncRunSerializer(run).data)


class RealSyncRunListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ProviderSyncRunSerializer

    def get_queryset(self):
        queryset = ProviderSyncRun.objects.order_by('-started_at', '-id')
        provider = self.request.query_params.get('provider')
        if provider:
            queryset = queryset.filter(provider=provider)
        limit = self.request.query_params.get('limit')
        if limit and limit.isdigit():
            return queryset[: int(limit)]
        return queryset[:50]


class RealSyncRunDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ProviderSyncRunSerializer
    queryset = ProviderSyncRun.objects.order_by('-started_at', '-id')


class RealSyncStatusView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        status = build_sync_status()
        payload = {
            'providers': status['providers'],
            'stale_after_minutes': status['stale_after_minutes'],
        }
        serializer = RealSyncStatusSerializer(payload)
        return Response(serializer.data)


class RealSyncSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        total = ProviderSyncRun.objects.count()
        by_status = dict(ProviderSyncRun.objects.values_list('status').annotate(count=Count('id')))
        by_provider = dict(ProviderSyncRun.objects.values_list('provider').annotate(count=Count('id')))
        payload = {
            'total_runs': total,
            'by_status': by_status,
            'by_provider': by_provider,
        }
        serializer = RealSyncSummarySerializer(payload)
        return Response(serializer.data)
