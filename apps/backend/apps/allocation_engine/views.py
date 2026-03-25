from django.db.models import Count, Sum
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.allocation_engine.models import AllocationDecision, AllocationRun
from apps.allocation_engine.serializers import (
    AllocationEvaluateRequestSerializer,
    AllocationEvaluateResponseSerializer,
    AllocationRunSerializer,
    AllocationSummarySerializer,
)
from apps.allocation_engine.services import AllocationConfig, evaluate_allocation


class AllocationEvaluateView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = AllocationEvaluateRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        default_cfg = AllocationConfig()
        config = AllocationConfig(
            max_candidates_considered=data.get('max_candidates', default_cfg.max_candidates_considered),
            max_executions_per_run=data.get('max_executions', default_cfg.max_executions_per_run),
        )
        result = evaluate_allocation(scope_type=data['scope_type'], triggered_from=data.get('triggered_from', 'manual'), config=config, persist=False)
        payload = {
            **result,
            'details': [
                {
                    'proposal_id': item['proposal'].id,
                    'market': item['proposal'].market.title,
                    'direction': item['proposal'].direction,
                    'proposal_score': str(item['proposal'].proposal_score),
                    'confidence': str(item['proposal'].confidence),
                    'suggested_quantity': str(item['proposal'].suggested_quantity or '0.0000'),
                    'final_allocated_quantity': str(item['final_allocated_quantity']),
                    'decision': item['decision'],
                    'rank': item['rank'],
                    'source_type': item['proposal'].market.source_type,
                    'provider': item['proposal'].market.provider.slug,
                    'rationale': item['rationale'],
                }
                for item in result['details']
            ],
            'run_id': None,
        }
        return Response(AllocationEvaluateResponseSerializer(payload).data, status=status.HTTP_200_OK)


class AllocationRunView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = AllocationEvaluateRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        default_cfg = AllocationConfig()
        config = AllocationConfig(
            max_candidates_considered=data.get('max_candidates', default_cfg.max_candidates_considered),
            max_executions_per_run=data.get('max_executions', default_cfg.max_executions_per_run),
        )
        result = evaluate_allocation(scope_type=data['scope_type'], triggered_from=data.get('triggered_from', 'manual'), config=config, persist=True)
        run = result['run']
        payload = {
            **result,
            'details': [
                {
                    'proposal_id': item['proposal'].id,
                    'market': item['proposal'].market.title,
                    'direction': item['proposal'].direction,
                    'proposal_score': str(item['proposal'].proposal_score),
                    'confidence': str(item['proposal'].confidence),
                    'suggested_quantity': str(item['proposal'].suggested_quantity or '0.0000'),
                    'final_allocated_quantity': str(item['final_allocated_quantity']),
                    'decision': item['decision'],
                    'rank': item['rank'],
                    'source_type': item['proposal'].market.source_type,
                    'provider': item['proposal'].market.provider.slug,
                    'rationale': item['rationale'],
                }
                for item in result['details']
            ],
            'run_id': run.id if run else None,
        }
        return Response(AllocationEvaluateResponseSerializer(payload).data, status=status.HTTP_200_OK)


class AllocationRunListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = AllocationRunSerializer

    def get_queryset(self):
        return AllocationRun.objects.prefetch_related('decisions', 'decisions__proposal', 'decisions__proposal__market', 'decisions__proposal__market__provider').order_by('-started_at', '-id')[:50]


class AllocationRunDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = AllocationRunSerializer
    queryset = AllocationRun.objects.prefetch_related('decisions', 'decisions__proposal', 'decisions__proposal__market', 'decisions__proposal__market__provider').order_by('-started_at', '-id')


class AllocationSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        latest_run = AllocationRun.objects.order_by('-started_at', '-id').first()
        decision_totals = AllocationDecision.objects.values('decision').annotate(total=Count('id'))
        selected_total = sum(item['total'] for item in decision_totals if item['decision'] in {'SELECTED', 'REDUCED'})
        rejected_total = sum(item['total'] for item in decision_totals if item['decision'] in {'REJECTED'})
        total_alloc = AllocationRun.objects.aggregate(total=Sum('allocated_total')).get('total') or 0
        payload = {
            'total_runs': AllocationRun.objects.count(),
            'latest_run': latest_run,
            'selected_total': selected_total,
            'rejected_total': rejected_total,
            'allocated_total': total_alloc,
        }
        return Response(AllocationSummarySerializer(payload).data, status=status.HTTP_200_OK)
