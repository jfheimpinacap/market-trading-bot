from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chaos_lab.models import ChaosExperiment, ChaosRun, ResilienceBenchmark
from apps.chaos_lab.serializers import ChaosExperimentSerializer, ChaosRunRequestSerializer, ChaosRunSerializer, ResilienceBenchmarkSerializer
from apps.chaos_lab.services import ensure_default_experiments, execute_chaos_run


class ChaosExperimentListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ChaosExperimentSerializer

    def get_queryset(self):
        ensure_default_experiments()
        return ChaosExperiment.objects.filter(is_enabled=True).order_by('severity', 'name', 'id')


class ChaosRunCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        ensure_default_experiments()
        serializer = ChaosRunRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        experiment = get_object_or_404(ChaosExperiment, pk=serializer.validated_data['experiment_id'], is_enabled=True)
        run = execute_chaos_run(experiment=experiment, trigger_mode=serializer.validated_data.get('trigger_mode', 'manual'))
        code = status.HTTP_201_CREATED if run.status in {'SUCCESS', 'PARTIAL'} else status.HTTP_400_BAD_REQUEST
        return Response(ChaosRunSerializer(run).data, status=code)


class ChaosRunListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ChaosRunSerializer

    def get_queryset(self):
        return ChaosRun.objects.select_related('experiment', 'benchmark').prefetch_related('observations').order_by('-created_at', '-id')[:100]


class ChaosRunDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ChaosRunSerializer
    queryset = ChaosRun.objects.select_related('experiment', 'benchmark').prefetch_related('observations').order_by('-created_at', '-id')


class ChaosBenchmarkListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ResilienceBenchmarkSerializer

    def get_queryset(self):
        return ResilienceBenchmark.objects.select_related('experiment', 'run').order_by('-created_at', '-id')[:100]


class ChaosSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        ensure_default_experiments()
        latest_run = ChaosRun.objects.select_related('experiment', 'benchmark').order_by('-created_at', '-id').first()
        benchmarks = ResilienceBenchmark.objects.order_by('-created_at', '-id')[:25]
        avg_score = 0
        if benchmarks:
            avg_score = round(sum(float(item.resilience_score) for item in benchmarks) / len(benchmarks), 2)

        return Response(
            {
                'latest_run': ChaosRunSerializer(latest_run).data if latest_run else None,
                'recent_runs': ChaosRunSerializer(ChaosRun.objects.select_related('experiment', 'benchmark').order_by('-created_at', '-id')[:10], many=True).data,
                'recent_benchmarks': ResilienceBenchmarkSerializer(benchmarks, many=True).data,
                'total_runs': ChaosRun.objects.count(),
                'success_runs': ChaosRun.objects.filter(status='SUCCESS').count(),
                'partial_runs': ChaosRun.objects.filter(status='PARTIAL').count(),
                'average_resilience_score': avg_score,
            },
            status=status.HTTP_200_OK,
        )
