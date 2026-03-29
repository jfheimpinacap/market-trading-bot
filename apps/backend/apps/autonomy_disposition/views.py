from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.autonomy_campaign.models import AutonomyCampaign
from apps.autonomy_disposition.models import CampaignDisposition, DispositionRecommendation, DispositionRun
from apps.autonomy_disposition.serializers import (
    CampaignDispositionActionSerializer,
    CampaignDispositionSerializer,
    DispositionRecommendationSerializer,
    RunDispositionReviewSerializer,
)
from apps.autonomy_disposition.services import apply_disposition, build_disposition_candidates, request_disposition_approval, run_disposition_review
from apps.autonomy_disposition.services.readiness import evaluate_disposition_readiness
from apps.autonomy_disposition.services.recommendation import build_disposition_recommendation_payload


class AutonomyDispositionCandidatesView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = []
        for context in build_disposition_candidates():
            readiness = evaluate_disposition_readiness(context)
            recommendation = build_disposition_recommendation_payload(context=context, readiness=readiness)
            rows.append(
                {
                    'campaign': context.campaign.id,
                    'campaign_title': context.campaign.title,
                    'campaign_status': context.campaign.status,
                    'recovery_status': context.recovery_snapshot.recovery_status if context.recovery_snapshot else None,
                    'last_intervention_outcome': context.last_intervention_outcome.outcome_type if context.last_intervention_outcome else None,
                    'last_runtime_status': context.last_runtime_snapshot.runtime_status if context.last_runtime_snapshot else None,
                    'disposition_readiness': readiness['disposition_readiness'],
                    'open_blockers': readiness['blockers'],
                    'pending_approvals_count': context.pending_approvals_count,
                    'unresolved_checkpoints_count': context.pending_checkpoints_count,
                    'unresolved_incident_pressure': context.unresolved_incident_pressure,
                    'closure_risk_level': readiness['closure_risk_level'],
                    'recommended_disposition': recommendation['disposition_type'],
                    'metadata': {
                        'reason_codes': readiness['reason_codes'],
                        'requires_approval': recommendation['requires_approval'],
                    },
                }
            )
        return Response(rows, status=status.HTTP_200_OK)


class AutonomyDispositionRunReviewView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RunDispositionReviewSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        result = run_disposition_review(actor=serializer.validated_data['actor'])
        return Response(
            {'run': result['run'].id, 'disposition_count': len(result['dispositions']), 'recommendation_count': len(result['recommendations'])},
            status=status.HTTP_200_OK,
        )


class AutonomyDispositionRecommendationsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = DispositionRecommendation.objects.select_related('target_campaign').order_by('-created_at', '-id')[:200]
        return Response(DispositionRecommendationSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomyDispositionListView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = CampaignDisposition.objects.select_related('campaign', 'linked_approval_request').order_by('-created_at', '-id')[:200]
        return Response(CampaignDispositionSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomyDispositionSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        latest = DispositionRun.objects.order_by('-created_at', '-id').first()
        return Response(
            {
                'latest_run_id': latest.id if latest else None,
                'candidate_count': latest.candidate_count if latest else 0,
                'ready_to_close_count': latest.ready_to_close_count if latest else 0,
                'ready_to_abort_count': latest.ready_to_abort_count if latest else 0,
                'ready_to_retire_count': latest.ready_to_retire_count if latest else 0,
                'require_more_review_count': latest.require_more_review_count if latest else 0,
                'keep_open_count': latest.keep_open_count if latest else 0,
                'approval_required_count': latest.approval_required_count if latest else 0,
                'recommendation_summary': latest.recommendation_summary if latest else {},
            },
            status=status.HTTP_200_OK,
        )


class AutonomyDispositionRequestApprovalView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, campaign_id: int, *args, **kwargs):
        serializer = CampaignDispositionActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        campaign = get_object_or_404(AutonomyCampaign, pk=campaign_id)
        disposition = CampaignDisposition.objects.filter(campaign=campaign).order_by('-created_at', '-id').first()
        if not disposition:
            return Response({'detail': 'No disposition exists for campaign. Run review first.'}, status=status.HTTP_400_BAD_REQUEST)
        approval = request_disposition_approval(disposition=disposition, actor=serializer.validated_data['actor'])
        return Response({'approval_request_id': approval.id, 'status': approval.status}, status=status.HTTP_200_OK)


class AutonomyDispositionApplyView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, campaign_id: int, *args, **kwargs):
        serializer = CampaignDispositionActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        campaign = get_object_or_404(AutonomyCampaign, pk=campaign_id)
        disposition = CampaignDisposition.objects.filter(campaign=campaign).order_by('-created_at', '-id').first()
        if not disposition:
            return Response({'detail': 'No disposition exists for campaign. Run review first.'}, status=status.HTTP_400_BAD_REQUEST)
        disposition = apply_disposition(disposition=disposition, actor=serializer.validated_data['actor'])
        return Response({'disposition_id': disposition.id, 'status': disposition.disposition_status, 'campaign_status': disposition.campaign.status}, status=status.HTTP_200_OK)
