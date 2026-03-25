from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.experiment_lab.models import ExperimentRun, StrategyProfile
from apps.experiment_lab.serializers import ExperimentRunRequestSerializer, ExperimentRunSerializer, StrategyProfileSerializer
from apps.experiment_lab.services import compare_experiment_runs, execute_experiment, seed_strategy_profiles


class StrategyProfileListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = StrategyProfileSerializer

    def get_queryset(self):
        return StrategyProfile.objects.order_by('name', 'id')


class StrategyProfileDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = StrategyProfileSerializer
    queryset = StrategyProfile.objects.order_by('name', 'id')


class ExperimentRunCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = ExperimentRunRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        profile = get_object_or_404(StrategyProfile, pk=serializer.validated_data['strategy_profile_id'])
        result = execute_experiment(profile=profile, payload=serializer.validated_data)
        code = status.HTTP_201_CREATED if result.experiment_run.status in {'SUCCESS', 'PARTIAL'} else status.HTTP_400_BAD_REQUEST
        return Response(ExperimentRunSerializer(result.experiment_run).data, status=code)


class ExperimentRunListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ExperimentRunSerializer

    def get_queryset(self):
        return ExperimentRun.objects.select_related('strategy_profile', 'related_replay_run', 'related_evaluation_run').order_by('-created_at', '-id')[:50]


class ExperimentRunDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ExperimentRunSerializer
    queryset = ExperimentRun.objects.select_related('strategy_profile', 'related_replay_run', 'related_evaluation_run').order_by('-created_at', '-id')


class ExperimentComparisonView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        left_id = request.query_params.get('left_run_id')
        right_id = request.query_params.get('right_run_id')
        if not (left_id and right_id and left_id.isdigit() and right_id.isdigit()):
            return Response({'detail': 'Provide left_run_id and right_run_id query params.'}, status=status.HTTP_400_BAD_REQUEST)

        left = get_object_or_404(ExperimentRun.objects.select_related('strategy_profile'), pk=int(left_id))
        right = get_object_or_404(ExperimentRun.objects.select_related('strategy_profile'), pk=int(right_id))
        return Response(compare_experiment_runs(left, right), status=status.HTTP_200_OK)


class ExperimentSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        latest = ExperimentRun.objects.select_related('strategy_profile').order_by('-created_at', '-id').first()
        recent = ExperimentRun.objects.select_related('strategy_profile').order_by('-created_at', '-id')[:10]
        return Response(
            {
                'latest_run': ExperimentRunSerializer(latest).data if latest else None,
                'recent_runs': ExperimentRunSerializer(recent, many=True).data,
                'total_runs': ExperimentRun.objects.count(),
                'success_runs': ExperimentRun.objects.filter(status='SUCCESS').count(),
            },
            status=status.HTTP_200_OK,
        )


class SeedStrategyProfilesView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        return Response(seed_strategy_profiles(), status=status.HTTP_200_OK)
