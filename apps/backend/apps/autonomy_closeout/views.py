from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.autonomy_campaign.models import AutonomyCampaign
from apps.autonomy_closeout.models import CampaignCloseoutReport, CloseoutFinding, CloseoutRecommendation, CloseoutRun
from apps.autonomy_closeout.serializers import (
    CampaignCloseoutReportSerializer,
    CloseoutActionSerializer,
    CloseoutFindingSerializer,
    CloseoutRecommendationSerializer,
    RunCloseoutReviewSerializer,
)
from apps.autonomy_closeout.services import build_closeout_candidates, complete_closeout, run_closeout_review


class AutonomyCloseoutCandidatesView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = []
        for candidate in build_closeout_candidates():
            rows.append(
                {
                    'campaign': candidate.campaign.id,
                    'campaign_title': candidate.campaign.title,
                    'disposition_type': candidate.disposition.disposition_type,
                    'disposition_status': candidate.disposition.disposition_status,
                    'final_campaign_status': candidate.campaign.status,
                    'ready_for_closeout': candidate.ready_for_closeout,
                    'requires_postmortem': candidate.requires_postmortem,
                    'requires_memory_index': candidate.requires_memory_index,
                    'requires_roadmap_feedback': candidate.requires_roadmap_feedback,
                    'unresolved_blockers': candidate.unresolved_blockers,
                    'unresolved_approvals_count': candidate.unresolved_approvals_count,
                    'incident_history_level': candidate.incident_history_level,
                    'intervention_count': candidate.intervention_count,
                    'metadata': candidate.metadata,
                }
            )
        return Response(rows, status=status.HTTP_200_OK)


class AutonomyCloseoutRunReviewView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RunCloseoutReviewSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        result = run_closeout_review(actor=serializer.validated_data['actor'])
        return Response(
            {'run': result['run'].id, 'report_count': len(result['reports']), 'recommendation_count': len(result['recommendations'])},
            status=status.HTTP_200_OK,
        )


class AutonomyCloseoutReportsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = CampaignCloseoutReport.objects.select_related('campaign').order_by('-updated_at', '-id')[:200]
        return Response(CampaignCloseoutReportSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomyCloseoutFindingsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = CloseoutFinding.objects.select_related('closeout_report', 'closeout_report__campaign').order_by('-created_at', '-id')[:300]
        return Response(CloseoutFindingSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomyCloseoutRecommendationsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = CloseoutRecommendation.objects.select_related('target_campaign').order_by('-created_at', '-id')[:300]
        return Response(CloseoutRecommendationSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomyCloseoutSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        latest = CloseoutRun.objects.order_by('-created_at', '-id').first()
        return Response(
            {
                'latest_run_id': latest.id if latest else None,
                'candidate_count': latest.candidate_count if latest else 0,
                'ready_count': latest.ready_count if latest else 0,
                'blocked_count': latest.blocked_count if latest else 0,
                'requires_postmortem_count': latest.requires_postmortem_count if latest else 0,
                'requires_memory_index_count': latest.requires_memory_index_count if latest else 0,
                'requires_roadmap_feedback_count': latest.requires_roadmap_feedback_count if latest else 0,
                'completed_closeout_count': latest.completed_closeout_count if latest else 0,
                'recommendation_summary': latest.recommendation_summary if latest else {},
            },
            status=status.HTTP_200_OK,
        )


class AutonomyCloseoutCompleteView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, campaign_id: int, *args, **kwargs):
        serializer = CloseoutActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        campaign = get_object_or_404(AutonomyCampaign, pk=campaign_id)
        report = get_object_or_404(CampaignCloseoutReport, campaign=campaign)
        try:
            report = complete_closeout(report=report, actor=serializer.validated_data['actor'])
        except ValueError as error:
            return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'report_id': report.id, 'closeout_status': report.closeout_status}, status=status.HTTP_200_OK)
