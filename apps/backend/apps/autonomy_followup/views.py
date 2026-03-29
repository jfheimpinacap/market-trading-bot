from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.autonomy_campaign.models import AutonomyCampaign
from apps.autonomy_followup.models import CampaignFollowup, FollowupRecommendation, FollowupRun
from apps.autonomy_followup.serializers import (
    CampaignFollowupSerializer,
    FollowupActionSerializer,
    FollowupRecommendationSerializer,
    RunFollowupReviewSerializer,
)
from apps.autonomy_followup.services import build_followup_candidates, emit_followups_for_campaign, run_followup_review


class AutonomyFollowupCandidatesView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = []
        for candidate in build_followup_candidates():
            rows.append(
                {
                    'campaign': candidate.campaign_id,
                    'campaign_title': candidate.campaign_title,
                    'closeout_report': candidate.closeout_report_id,
                    'closeout_status': candidate.closeout_status,
                    'requires_postmortem': candidate.requires_postmortem,
                    'requires_memory_index': candidate.requires_memory_index,
                    'requires_roadmap_feedback': candidate.requires_roadmap_feedback,
                    'existing_memory_document': candidate.existing_memory_document,
                    'existing_postmortem_request': candidate.existing_postmortem_request,
                    'existing_feedback_artifact': candidate.existing_feedback_artifact,
                    'followup_readiness': candidate.followup_readiness,
                    'blockers': candidate.blockers,
                    'metadata': candidate.metadata,
                }
            )
        return Response(rows, status=status.HTTP_200_OK)


class AutonomyFollowupRunReviewView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RunFollowupReviewSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        result = run_followup_review(actor=serializer.validated_data['actor'])
        return Response(
            {'run': result['run'].id, 'candidate_count': len(result['candidates']), 'recommendation_count': len(result['recommendations'])},
            status=status.HTTP_200_OK,
        )


class AutonomyFollowupListView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = CampaignFollowup.objects.select_related('campaign', 'closeout_report', 'linked_memory_document', 'linked_postmortem_request').order_by('-updated_at', '-id')[:300]
        return Response(CampaignFollowupSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomyFollowupRecommendationsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = FollowupRecommendation.objects.select_related('target_campaign').order_by('-created_at', '-id')[:400]
        return Response(FollowupRecommendationSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomyFollowupSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        latest = FollowupRun.objects.order_by('-created_at', '-id').first()
        return Response(
            {
                'latest_run_id': latest.id if latest else None,
                'candidate_count': latest.candidate_count if latest else 0,
                'ready_count': latest.ready_count if latest else 0,
                'blocked_count': latest.blocked_count if latest else 0,
                'emitted_count': latest.emitted_count if latest else 0,
                'duplicate_skipped_count': latest.duplicate_skipped_count if latest else 0,
                'memory_followup_count': latest.memory_followup_count if latest else 0,
                'postmortem_followup_count': latest.postmortem_followup_count if latest else 0,
                'roadmap_feedback_count': latest.roadmap_feedback_count if latest else 0,
                'recommendation_summary': latest.recommendation_summary if latest else {},
            },
            status=status.HTTP_200_OK,
        )


class AutonomyFollowupEmitView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, campaign_id: int, *args, **kwargs):
        serializer = FollowupActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        campaign = get_object_or_404(AutonomyCampaign, pk=campaign_id)
        try:
            rows = emit_followups_for_campaign(campaign_id=campaign.id, actor=serializer.validated_data['actor'])
        except ValueError as error:
            return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'campaign': campaign.id, 'emitted_count': len(rows)}, status=status.HTTP_200_OK)
