from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.autonomy_program.models import AutonomyProgramState, CampaignHealthSnapshot, ProgramRecommendation
from apps.autonomy_program.serializers import (
    AutonomyProgramStateSerializer,
    CampaignConcurrencyRuleSerializer,
    CampaignHealthSnapshotSerializer,
    ProgramRecommendationSerializer,
    RunProgramReviewSerializer,
)
from apps.autonomy_program.services import build_program_state_payload, list_rules, run_program_review


class AutonomyProgramStateView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        payload = build_program_state_payload()
        return Response(
            {
                'state': AutonomyProgramStateSerializer(payload['state']).data,
                'conflicts': payload['conflicts'],
                'max_active_campaigns': payload['max_active_campaigns'],
                'critical_incident_active': payload['critical_incident_active'],
            },
            status=status.HTTP_200_OK,
        )


class AutonomyProgramRulesView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(CampaignConcurrencyRuleSerializer(list_rules(), many=True).data, status=status.HTTP_200_OK)


class AutonomyProgramRunReviewView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RunProgramReviewSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        result = run_program_review(
            actor=serializer.validated_data.get('actor') or 'operator-ui',
            apply_pause_gating=serializer.validated_data.get('apply_pause_gating', True),
        )
        return Response(
            {
                'state': AutonomyProgramStateSerializer(result['state']).data,
                'health_snapshots': CampaignHealthSnapshotSerializer(result['health_snapshots'], many=True).data,
                'recommendations': ProgramRecommendationSerializer(result['recommendations'], many=True).data,
                'pause_gates_applied': result['pause_gates_applied'],
                'conflicts': result['conflicts'],
            },
            status=status.HTTP_200_OK,
        )


class AutonomyProgramRecommendationsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = ProgramRecommendation.objects.select_related('target_campaign').order_by('-created_at', '-id')[:100]
        return Response(ProgramRecommendationSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomyProgramHealthView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = CampaignHealthSnapshot.objects.select_related('campaign').order_by('-created_at', '-id')[:100]
        return Response(CampaignHealthSnapshotSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomyProgramSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        state = AutonomyProgramState.objects.order_by('-created_at', '-id').first()
        if not state:
            payload = build_program_state_payload()
            state = payload['state']
        latest_recommendation = ProgramRecommendation.objects.order_by('-created_at', '-id').first()
        latest_health = CampaignHealthSnapshot.objects.order_by('-created_at', '-id').first()
        return Response(
            {
                'program_state_id': state.id,
                'concurrency_posture': state.concurrency_posture,
                'active_campaigns_count': state.active_campaigns_count,
                'blocked_campaigns_count': state.blocked_campaigns_count,
                'waiting_approval_count': state.waiting_approval_count,
                'observing_campaigns_count': state.observing_campaigns_count,
                'degraded_domains_count': state.degraded_domains_count,
                'locked_domains': state.locked_domains,
                'latest_recommendation_type': latest_recommendation.recommendation_type if latest_recommendation else None,
                'latest_recommendation_target': latest_recommendation.target_campaign_id if latest_recommendation else None,
                'latest_health_status': latest_health.health_status if latest_health else None,
                'latest_health_campaign_id': latest_health.campaign_id if latest_health else None,
            },
            status=status.HTTP_200_OK,
        )
