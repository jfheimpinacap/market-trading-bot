from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.experiment_lab.models import ExperimentRun, StrategyProfile
from apps.experiment_lab.serializers import (
    ExperimentCandidateSerializer,
    ExperimentPromotionRecommendationSerializer,
    ExperimentRunRequestSerializer,
    ExperimentRunSerializer,
    StrategyProfileSerializer,
    TuningChampionChallengerComparisonSerializer,
    TuningValidationRunRequestSerializer,
)
from apps.experiment_lab.services import (
    build_tuning_validation_summary,
    compare_experiment_runs,
    execute_experiment,
    run_tuning_validation,
    seed_strategy_profiles,
)
from apps.experiment_lab.models import ExperimentCandidate, ExperimentPromotionRecommendation, TuningChampionChallengerComparison


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


class RunTuningValidationView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = TuningValidationRunRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        run = run_tuning_validation(
            linked_tuning_review_run_id=serializer.validated_data.get('linked_tuning_review_run_id'),
            metadata=serializer.validated_data.get('metadata') or {},
        )
        return Response(
            {
                'run_id': run.id,
                'candidate_count': run.candidate_count,
                'comparison_count': run.comparison_count,
                'recommendation_summary': run.recommendation_summary,
            },
            status=status.HTTP_201_CREATED,
        )


class TuningCandidateListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ExperimentCandidateSerializer

    def get_queryset(self):
        queryset = ExperimentCandidate.objects.select_related('linked_tuning_proposal', 'linked_tuning_bundle', 'run').order_by('-created_at', '-id')
        component = self.request.query_params.get('component')
        scope = self.request.query_params.get('scope')
        readiness = self.request.query_params.get('readiness_status')
        if component:
            queryset = queryset.filter(linked_tuning_proposal__target_component=component)
        if scope:
            queryset = queryset.filter(experiment_scope=scope)
        if readiness:
            queryset = queryset.filter(readiness_status=readiness)
        return queryset[:200]


class ChampionChallengerComparisonListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = TuningChampionChallengerComparisonSerializer

    def get_queryset(self):
        queryset = TuningChampionChallengerComparison.objects.select_related('linked_candidate', 'run').order_by('-created_at', '-id')
        status_param = self.request.query_params.get('comparison_status')
        if status_param:
            queryset = queryset.filter(comparison_status=status_param)
        return queryset[:200]


class PromotionRecommendationListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ExperimentPromotionRecommendationSerializer

    def get_queryset(self):
        return ExperimentPromotionRecommendation.objects.select_related('target_candidate', 'target_comparison', 'run').order_by('-created_at', '-id')[:200]


class TuningValidationSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(build_tuning_validation_summary(), status=status.HTTP_200_OK)
