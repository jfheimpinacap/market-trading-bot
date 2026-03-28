from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.autonomy_roadmap.models import AutonomyRoadmapPlan, DomainDependency
from apps.autonomy_roadmap.serializers import (
    AutonomyRoadmapPlanSerializer,
    DomainDependencySerializer,
    RoadmapRecommendationSerializer,
    RunRoadmapPlanSerializer,
)
from apps.autonomy_roadmap.services.dependencies import list_dependencies
from apps.autonomy_roadmap.services.plans import build_summary_payload, list_plan_queryset, list_recommendations_queryset, run_roadmap_plan


class DomainDependencyListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = DomainDependencySerializer

    def get_queryset(self):
        list_dependencies()
        return DomainDependency.objects.select_related('source_domain', 'target_domain', 'source_domain__roadmap_profile', 'target_domain__roadmap_profile').order_by('source_domain__slug', 'target_domain__slug', 'dependency_type')


class RunAutonomyRoadmapPlanView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RunRoadmapPlanSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        plan = run_roadmap_plan(requested_by=serializer.validated_data.get('requested_by') or 'operator-ui')
        return Response(AutonomyRoadmapPlanSerializer(plan).data, status=status.HTTP_201_CREATED)


class AutonomyRoadmapPlanListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = AutonomyRoadmapPlanSerializer

    def get_queryset(self):
        return list_plan_queryset()[:50]


class AutonomyRoadmapPlanDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, pk: int, *args, **kwargs):
        plan = get_object_or_404(list_plan_queryset(), pk=pk)
        return Response(AutonomyRoadmapPlanSerializer(plan).data, status=status.HTTP_200_OK)


class RoadmapRecommendationListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = RoadmapRecommendationSerializer

    def get_queryset(self):
        limit = int(self.request.query_params.get('limit', '200'))
        return list_recommendations_queryset()[:max(1, min(limit, 500))]


class AutonomyRoadmapSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        summary = build_summary_payload()
        latest = None
        if summary['latest_plan_id']:
            latest = AutonomyRoadmapPlan.objects.filter(pk=summary['latest_plan_id']).first()
        summary['latest_plan'] = AutonomyRoadmapPlanSerializer(latest).data if latest else None
        return Response(summary, status=status.HTTP_200_OK)
