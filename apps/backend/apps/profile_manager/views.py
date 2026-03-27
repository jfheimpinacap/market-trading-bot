from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.profile_manager.models import ProfileDecision, ProfileGovernanceRun
from apps.profile_manager.serializers import (
    ProfileGovernanceRunSerializer,
    ProfileGovernanceSummarySerializer,
    RunProfileGovernanceSerializer,
)
from apps.profile_manager.services import apply_profile_decision, build_profile_governance_summary, list_bindings, run_profile_governance


class RunProfileGovernanceView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RunProfileGovernanceSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        run = run_profile_governance(
            decision_mode=serializer.validated_data.get('decision_mode'),
            triggered_by=serializer.validated_data.get('triggered_by', 'manual_api'),
        )
        return Response(ProfileGovernanceRunSerializer(run).data, status=status.HTTP_200_OK)


class ProfileGovernanceRunListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ProfileGovernanceRunSerializer

    def get_queryset(self):
        return ProfileGovernanceRun.objects.select_related('decision').order_by('-started_at', '-id')[:100]


class ProfileGovernanceRunDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ProfileGovernanceRunSerializer
    queryset = ProfileGovernanceRun.objects.select_related('decision').order_by('-started_at', '-id')


class CurrentProfileGovernanceView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        current = ProfileGovernanceRun.objects.select_related('decision').order_by('-started_at', '-id').first()
        if current is None:
            return Response({'detail': 'No profile governance run available yet.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(ProfileGovernanceRunSerializer(current).data, status=status.HTTP_200_OK)


class ProfileGovernanceSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        payload = build_profile_governance_summary()
        payload['available_bindings'] = list_bindings()
        serialized = ProfileGovernanceSummarySerializer(payload)
        return Response(serialized.data, status=status.HTTP_200_OK)


class ApplyProfileDecisionView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, decision_id: int, *args, **kwargs):
        decision = ProfileDecision.objects.select_related('run').filter(pk=decision_id).first()
        if decision is None:
            return Response({'detail': 'Profile decision not found.'}, status=status.HTTP_404_NOT_FOUND)
        apply_profile_decision(decision, applied_by='manual_apply_api')
        return Response({'status': 'applied', 'decision_id': decision.id}, status=status.HTTP_200_OK)
