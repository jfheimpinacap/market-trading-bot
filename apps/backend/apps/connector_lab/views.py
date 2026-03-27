from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.connector_lab.models import AdapterQualificationRun, AdapterReadinessRecommendation
from apps.connector_lab.serializers import AdapterQualificationRunSerializer, AdapterReadinessRecommendationSerializer, RunQualificationRequestSerializer
from apps.connector_lab.services import build_summary, ensure_fixture_profiles, execute_qualification_suite, get_fixture_profile, list_cases


class ConnectorCasesView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        fixtures = ensure_fixture_profiles()
        return Response({'cases': list_cases(), 'fixtures': [{'slug': fixture.slug, 'display_name': fixture.display_name, 'description': fixture.description} for fixture in fixtures]}, status=status.HTTP_200_OK)


class ConnectorRunQualificationView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RunQualificationRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        fixture = get_fixture_profile(serializer.validated_data.get('fixture_profile'))
        run = execute_qualification_suite(fixture_profile=fixture, metadata=serializer.validated_data.get('metadata') or {})
        return Response(AdapterQualificationRunSerializer(run).data, status=status.HTTP_201_CREATED)


class ConnectorRunsView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = AdapterQualificationRunSerializer

    def get_queryset(self):
        return AdapterQualificationRun.objects.select_related('fixture_profile', 'readiness_recommendation').prefetch_related('results').order_by('-created_at', '-id')[:50]


class ConnectorRunDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = AdapterQualificationRunSerializer
    queryset = AdapterQualificationRun.objects.select_related('fixture_profile', 'readiness_recommendation').prefetch_related('results')


class ConnectorCurrentReadinessView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        readiness = AdapterReadinessRecommendation.objects.select_related('qualification_run').order_by('-created_at', '-id').first()
        if not readiness:
            return Response({'detail': 'No readiness recommendation generated yet.'}, status=status.HTTP_200_OK)
        return Response(AdapterReadinessRecommendationSerializer(readiness).data, status=status.HTTP_200_OK)


class ConnectorSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(build_summary(), status=status.HTTP_200_OK)
