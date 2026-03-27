from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.champion_challenger.models import ChampionChallengerRun, ChampionChallengerRunStatus, StackProfileBinding
from apps.champion_challenger.serializers import (
    ChampionChallengerRunRequestSerializer,
    ChampionChallengerRunSerializer,
    SetChampionBindingSerializer,
    StackProfileBindingSerializer,
)
from apps.champion_challenger.services import get_or_create_champion_binding, run_shadow_benchmark, set_champion_binding


class ChampionChallengerRunCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = ChampionChallengerRunRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        run = run_shadow_benchmark(payload=serializer.validated_data)
        code = status.HTTP_201_CREATED if run.status == ChampionChallengerRunStatus.COMPLETED else status.HTTP_400_BAD_REQUEST
        return Response(ChampionChallengerRunSerializer(run).data, status=code)


class ChampionChallengerRunListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ChampionChallengerRunSerializer

    def get_queryset(self):
        return ChampionChallengerRun.objects.select_related('champion_binding', 'challenger_binding').prefetch_related('comparison_result').order_by('-created_at', '-id')[:50]


class ChampionChallengerRunDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ChampionChallengerRunSerializer
    queryset = ChampionChallengerRun.objects.select_related('champion_binding', 'challenger_binding').prefetch_related('comparison_result').order_by('-created_at', '-id')


class CurrentChampionBindingView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        binding = get_or_create_champion_binding()
        return Response({'current_champion': StackProfileBindingSerializer(binding).data}, status=status.HTTP_200_OK)


class ChampionChallengerSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        latest = ChampionChallengerRun.objects.select_related('champion_binding', 'challenger_binding').prefetch_related('comparison_result').order_by('-created_at', '-id').first()
        recent = ChampionChallengerRun.objects.select_related('champion_binding', 'challenger_binding').prefetch_related('comparison_result').order_by('-created_at', '-id')[:10]
        return Response(
            {
                'current_champion': StackProfileBindingSerializer(get_or_create_champion_binding()).data,
                'latest_run': ChampionChallengerRunSerializer(latest).data if latest else None,
                'recent_runs': ChampionChallengerRunSerializer(recent, many=True).data,
                'total_runs': ChampionChallengerRun.objects.count(),
                'completed_runs': ChampionChallengerRun.objects.filter(status=ChampionChallengerRunStatus.COMPLETED).count(),
            },
            status=status.HTTP_200_OK,
        )


class SetChampionBindingView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = SetChampionBindingSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        binding = get_object_or_404(StackProfileBinding, pk=serializer.validated_data['binding_id'])
        binding = set_champion_binding(binding=binding)
        return Response(StackProfileBindingSerializer(binding).data, status=status.HTTP_200_OK)
