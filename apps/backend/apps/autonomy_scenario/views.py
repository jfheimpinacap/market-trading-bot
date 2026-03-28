from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.autonomy_scenario.serializers import AutonomyScenarioRunSerializer, RunAutonomyScenarioSerializer, ScenarioRecommendationSerializer
from apps.autonomy_scenario.services import build_summary_payload, get_options_preview, list_recommendations_queryset, list_runs_queryset, run_simulation


class RunAutonomyScenarioView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RunAutonomyScenarioSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        run = run_simulation(
            requested_by=serializer.validated_data.get('requested_by') or 'operator-ui',
            notes=serializer.validated_data.get('notes') or '',
        )
        return Response(AutonomyScenarioRunSerializer(run).data, status=status.HTTP_201_CREATED)


class AutonomyScenarioRunListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = AutonomyScenarioRunSerializer

    def get_queryset(self):
        return list_runs_queryset()[:50]


class AutonomyScenarioRunDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, pk: int, *args, **kwargs):
        run = get_object_or_404(list_runs_queryset(), pk=pk)
        return Response(AutonomyScenarioRunSerializer(run).data, status=status.HTTP_200_OK)


class AutonomyScenarioOptionsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response({'options': get_options_preview()}, status=status.HTTP_200_OK)


class AutonomyScenarioRecommendationListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ScenarioRecommendationSerializer

    def get_queryset(self):
        return list_recommendations_queryset()[:200]


class AutonomyScenarioSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(build_summary_payload(), status=status.HTTP_200_OK)
