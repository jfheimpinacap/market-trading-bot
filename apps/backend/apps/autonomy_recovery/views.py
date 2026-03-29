from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.autonomy_campaign.models import AutonomyCampaign
from apps.autonomy_recovery.models import RecoveryRecommendation, RecoveryRun, RecoverySnapshot
from apps.autonomy_recovery.serializers import (
    RecoveryCampaignActionSerializer,
    RecoveryRecommendationSerializer,
    RecoverySnapshotSerializer,
    RunRecoveryReviewSerializer,
)
from apps.autonomy_recovery.services import build_recovery_candidates, request_close_approval, request_resume_approval, run_recovery_review
from apps.autonomy_recovery.services.readiness import evaluate_recovery_readiness


class AutonomyRecoveryCandidatesView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = []
        for context in build_recovery_candidates():
            readiness = evaluate_recovery_readiness(context)
            rows.append(
                {
                    'campaign': context.campaign.id,
                    'campaign_title': context.campaign.title,
                    'campaign_status': context.campaign.status,
                    'last_intervention_request': context.last_request.id if context.last_request else None,
                    'last_intervention_action': context.last_action.id if context.last_action else None,
                    'last_intervention_outcome': context.last_outcome.id if context.last_outcome else None,
                    'paused_or_blocked_since': context.campaign.updated_at,
                    'current_wave': context.campaign.current_wave,
                    'current_step': context.runtime.current_step_id if context.runtime else None,
                    'open_blockers': readiness['blockers'],
                    'pending_approvals_count': context.pending_approvals_count,
                    'pending_checkpoints_count': context.pending_checkpoints_count,
                    'incident_impact': context.incident_impact,
                    'degraded_impact': context.degraded_impact,
                    'rollout_observation_impact': context.rollout_observation_impact,
                    'recovery_status': readiness['recovery_status'],
                    'metadata': {
                        'resume_readiness': readiness['resume_readiness'],
                        'recovery_priority': readiness['recovery_priority'],
                    },
                }
            )
        return Response(rows, status=status.HTTP_200_OK)


class AutonomyRecoveryRunReviewView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RunRecoveryReviewSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        result = run_recovery_review(actor=serializer.validated_data['actor'])
        return Response(
            {
                'run': result['run'].id,
                'snapshot_count': len(result['snapshots']),
                'recommendation_count': len(result['recommendations']),
            },
            status=status.HTTP_200_OK,
        )


class AutonomyRecoverySnapshotsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = RecoverySnapshot.objects.select_related('campaign').order_by('-created_at', '-id')[:200]
        return Response(RecoverySnapshotSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomyRecoverySnapshotsByCampaignView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, campaign_id: int, *args, **kwargs):
        rows = RecoverySnapshot.objects.select_related('campaign').filter(campaign_id=campaign_id).order_by('-created_at', '-id')[:50]
        return Response(RecoverySnapshotSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomyRecoveryRecommendationsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = RecoveryRecommendation.objects.select_related('target_campaign').order_by('-created_at', '-id')[:200]
        return Response(RecoveryRecommendationSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomyRecoverySummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        latest = RecoveryRun.objects.order_by('-created_at', '-id').first()
        return Response(
            {
                'latest_run_id': latest.id if latest else None,
                'candidate_count': latest.candidate_count if latest else 0,
                'ready_to_resume_count': latest.ready_to_resume_count if latest else 0,
                'keep_paused_count': latest.keep_paused_count if latest else 0,
                'blocked_count': latest.blocked_count if latest else 0,
                'review_abort_count': latest.review_abort_count if latest else 0,
                'close_candidate_count': latest.close_candidate_count if latest else 0,
                'approval_required_count': latest.approval_required_count if latest else 0,
                'recommendation_summary': latest.recommendation_summary if latest else {},
            },
            status=status.HTTP_200_OK,
        )


class AutonomyRecoveryRequestResumeApprovalView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, campaign_id: int, *args, **kwargs):
        serializer = RecoveryCampaignActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        campaign = get_object_or_404(AutonomyCampaign, pk=campaign_id)
        approval = request_resume_approval(campaign=campaign, actor=serializer.validated_data['actor'])
        return Response({'approval_request_id': approval.id, 'status': approval.status}, status=status.HTTP_200_OK)


class AutonomyRecoveryRequestCloseApprovalView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, campaign_id: int, *args, **kwargs):
        serializer = RecoveryCampaignActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        campaign = get_object_or_404(AutonomyCampaign, pk=campaign_id)
        approval = request_close_approval(campaign=campaign, actor=serializer.validated_data['actor'])
        return Response({'approval_request_id': approval.id, 'status': approval.status}, status=status.HTTP_200_OK)
