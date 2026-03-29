from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.autonomy_insights.models import CampaignInsight, InsightRecommendation, InsightRun
from apps.autonomy_insights.serializers import (
    CampaignInsightSerializer,
    InsightActionSerializer,
    InsightRecommendationSerializer,
    RunInsightReviewSerializer,
)
from apps.autonomy_insights.services import build_insight_candidates, mark_insight_reviewed, run_insight_review


class AutonomyInsightCandidatesView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = []
        for candidate in build_insight_candidates():
            rows.append(
                {
                    'campaign': candidate.campaign_id,
                    'campaign_title': candidate.campaign_title,
                    'closeout_status': candidate.closeout_status,
                    'feedback_resolution_status': candidate.feedback_resolution_status,
                    'disposition_type': candidate.disposition_type,
                    'lifecycle_closed': candidate.lifecycle_closed,
                    'major_failure_modes': candidate.major_failure_modes,
                    'major_success_factors': candidate.major_success_factors,
                    'approval_friction_level': candidate.approval_friction_level,
                    'incident_pressure_level': candidate.incident_pressure_level,
                    'recovery_complexity_level': candidate.recovery_complexity_level,
                    'roadmap_feedback_present': candidate.roadmap_feedback_present,
                    'memory_followup_resolved': candidate.memory_followup_resolved,
                    'postmortem_followup_resolved': candidate.postmortem_followup_resolved,
                    'metadata': candidate.metadata,
                }
            )
        return Response(rows, status=status.HTTP_200_OK)


class AutonomyInsightRunReviewView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RunInsightReviewSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        result = run_insight_review(actor=serializer.validated_data['actor'])
        return Response(
            {
                'run': result['run'].id,
                'candidate_count': len(result['candidates']),
                'insight_count': len(result['insights']),
                'recommendation_count': len(result['recommendations']),
            },
            status=status.HTTP_200_OK,
        )


class AutonomyInsightListView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = CampaignInsight.objects.select_related('campaign').order_by('-created_at', '-id')[:400]
        return Response(CampaignInsightSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomyInsightRecommendationsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = InsightRecommendation.objects.select_related('target_campaign', 'campaign_insight').order_by('-created_at', '-id')[:500]
        return Response(InsightRecommendationSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomyInsightSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        latest = InsightRun.objects.order_by('-created_at', '-id').first()
        pending_review_count = CampaignInsight.objects.filter(reviewed=False).count()
        return Response(
            {
                'latest_run_id': latest.id if latest else None,
                'candidate_count': latest.candidate_count if latest else 0,
                'lifecycle_closed_count': latest.lifecycle_closed_count if latest else 0,
                'insight_count': latest.insight_count if latest else 0,
                'success_pattern_count': latest.success_pattern_count if latest else 0,
                'failure_pattern_count': latest.failure_pattern_count if latest else 0,
                'blocker_pattern_count': latest.blocker_pattern_count if latest else 0,
                'governance_pattern_count': latest.governance_pattern_count if latest else 0,
                'pending_review_count': pending_review_count,
                'recommendation_summary': latest.recommendation_summary if latest else {},
            },
            status=status.HTTP_200_OK,
        )


class AutonomyInsightDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, insight_id: int, *args, **kwargs):
        try:
            row = CampaignInsight.objects.select_related('campaign').get(id=insight_id)
        except CampaignInsight.DoesNotExist:
            return Response({'detail': 'Insight not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(CampaignInsightSerializer(row).data, status=status.HTTP_200_OK)


class AutonomyInsightMarkReviewedView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, insight_id: int, *args, **kwargs):
        serializer = InsightActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        try:
            insight = mark_insight_reviewed(insight_id=insight_id, actor=serializer.validated_data['actor'])
        except CampaignInsight.DoesNotExist:
            return Response({'detail': 'Insight not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'insight_id': insight.id, 'reviewed': insight.reviewed}, status=status.HTTP_200_OK)
