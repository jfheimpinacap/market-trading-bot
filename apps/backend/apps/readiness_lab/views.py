from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.readiness_lab.models import ReadinessAssessmentRun, ReadinessProfile
from apps.readiness_lab.serializers import (
    ReadinessAssessmentRequestSerializer,
    ReadinessAssessmentRunSerializer,
    ReadinessProfileSerializer,
)
from apps.readiness_lab.services import get_readiness_summary, run_readiness_assessment, seed_readiness_profiles


class ReadinessProfileListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ReadinessProfileSerializer

    def get_queryset(self):
        return ReadinessProfile.objects.order_by('name', 'id')


class ReadinessProfileDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ReadinessProfileSerializer
    queryset = ReadinessProfile.objects.order_by('name', 'id')


class ReadinessAssessView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = ReadinessAssessmentRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        profile = get_object_or_404(ReadinessProfile, pk=serializer.validated_data['readiness_profile_id'])
        run = run_readiness_assessment(profile)
        return Response(ReadinessAssessmentRunSerializer(run).data, status=status.HTTP_201_CREATED)


class ReadinessRunListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ReadinessAssessmentRunSerializer

    def get_queryset(self):
        return ReadinessAssessmentRun.objects.select_related('readiness_profile').order_by('-created_at', '-id')[:50]


class ReadinessRunDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ReadinessAssessmentRunSerializer
    queryset = ReadinessAssessmentRun.objects.select_related('readiness_profile').order_by('-created_at', '-id')


class ReadinessSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        summary = get_readiness_summary()
        payload = {
            'latest_run': ReadinessAssessmentRunSerializer(summary['latest_run']).data if summary['latest_run'] else None,
            'recent_runs': ReadinessAssessmentRunSerializer(summary['recent_runs'], many=True).data,
            'total_runs': summary['total_runs'],
            'ready_runs': summary['ready_runs'],
            'caution_runs': summary['caution_runs'],
            'not_ready_runs': summary['not_ready_runs'],
        }
        return Response(payload, status=status.HTTP_200_OK)


class ReadinessSeedProfilesView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        return Response(seed_readiness_profiles(), status=status.HTTP_200_OK)
