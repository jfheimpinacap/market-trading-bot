from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.real_data_sync.services import build_sync_status
from apps.real_market_ops.models import RealMarketOperationRun
from apps.real_market_ops.serializers import RealMarketOperationRunSerializer, RealMarketOpsStatusSerializer, RealMarketRunRequestSerializer
from apps.real_market_ops.services import RunOptions, evaluate_real_market_eligibility, get_real_scope_payload, run_real_market_operation


class RealMarketOpsEvaluateView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        snapshot = evaluate_real_market_eligibility()
        payload = {
            'scope': snapshot.scope,
            'providers_considered': snapshot.providers_considered,
            'provider_status': snapshot.provider_status,
            'markets_considered': snapshot.counters['markets_considered'],
            'markets_eligible': snapshot.counters['markets_eligible'],
            'excluded_count': snapshot.counters['excluded_count'],
            'skipped_stale_count': snapshot.counters['skipped_stale_count'],
            'skipped_degraded_provider_count': snapshot.counters['skipped_degraded_provider_count'],
            'skipped_no_pricing_count': snapshot.counters['skipped_no_pricing_count'],
            'eligible_markets': [
                {'id': market.id, 'title': market.title, 'provider': market.provider.slug, 'category': market.category}
                for market in snapshot.eligible
            ],
            'excluded_markets': snapshot.excluded,
        }
        return Response(payload, status=status.HTTP_200_OK)


class RealMarketOpsRunView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RealMarketRunRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        run = run_real_market_operation(
            options=RunOptions(
                execute_auto=True,
                triggered_from=serializer.validated_data['triggered_from'],
            )
        )
        return Response(RealMarketOperationRunSerializer(run).data, status=status.HTTP_200_OK)


class RealMarketOpsRunListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = RealMarketOperationRunSerializer

    def get_queryset(self):
        limit = self.request.query_params.get('limit')
        queryset = RealMarketOperationRun.objects.order_by('-started_at', '-id')
        if limit and limit.isdigit():
            return queryset[: int(limit)]
        return queryset[:50]


class RealMarketOpsRunDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = RealMarketOperationRunSerializer
    queryset = RealMarketOperationRun.objects.order_by('-started_at', '-id')


class RealMarketOpsStatusView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        sync_status = build_sync_status()
        latest_run = RealMarketOperationRun.objects.order_by('-started_at', '-id').first()
        payload = {
            'enabled': get_real_scope_payload()['enabled'],
            'execution_mode': 'paper_demo_only',
            'source_type_required': 'real_read_only',
            'provider_status': sync_status['providers'],
            'scope': get_real_scope_payload(),
            'latest_run': RealMarketOperationRunSerializer(latest_run).data if latest_run else None,
        }
        serializer = RealMarketOpsStatusSerializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RealMarketEligibleMarketsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        snapshot = evaluate_real_market_eligibility()
        return Response(
            {
                'eligible_markets': [
                    {'id': market.id, 'title': market.title, 'provider': market.provider.slug, 'category': market.category}
                    for market in snapshot.eligible
                ],
                'excluded_markets': snapshot.excluded,
            },
            status=status.HTTP_200_OK,
        )
