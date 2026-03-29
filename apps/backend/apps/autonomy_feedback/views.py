from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.autonomy_feedback.models import FeedbackRecommendation, FeedbackRun, FollowupResolution
from apps.autonomy_feedback.serializers import (
    FeedbackActionSerializer,
    FeedbackRecommendationSerializer,
    FollowupResolutionSerializer,
    RunFeedbackReviewSerializer,
)
from apps.autonomy_feedback.services import build_feedback_candidates, mark_resolution_complete, run_feedback_review
from apps.autonomy_followup.models import CampaignFollowup


class AutonomyFeedbackCandidatesView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = []
        for candidate in build_feedback_candidates():
            rows.append(
                {
                    'campaign': candidate.campaign_id,
                    'campaign_title': candidate.campaign_title,
                    'followup': candidate.followup_id,
                    'followup_type': candidate.followup_type,
                    'followup_status': candidate.followup_status,
                    'linked_artifact': candidate.linked_artifact,
                    'downstream_status': candidate.downstream_status,
                    'ready_for_resolution': candidate.ready_for_resolution,
                    'blockers': candidate.blockers,
                    'metadata': candidate.metadata,
                }
            )
        return Response(rows, status=status.HTTP_200_OK)


class AutonomyFeedbackRunReviewView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RunFeedbackReviewSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        result = run_feedback_review(actor=serializer.validated_data['actor'])
        return Response(
            {
                'run': result['run'].id,
                'candidate_count': len(result['candidates']),
                'resolution_count': len(result['resolutions']),
                'recommendation_count': len(result['recommendations']),
            },
            status=status.HTTP_200_OK,
        )


class AutonomyFeedbackResolutionsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = FollowupResolution.objects.select_related('campaign', 'followup').order_by('-updated_at', '-id')[:300]
        return Response(FollowupResolutionSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomyFeedbackRecommendationsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = FeedbackRecommendation.objects.select_related('target_campaign', 'followup').order_by('-created_at', '-id')[:400]
        return Response(FeedbackRecommendationSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomyFeedbackSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        latest = FeedbackRun.objects.order_by('-created_at', '-id').first()
        return Response(
            {
                'latest_run_id': latest.id if latest else None,
                'candidate_count': latest.candidate_count if latest else 0,
                'pending_count': latest.pending_count if latest else 0,
                'in_progress_count': latest.in_progress_count if latest else 0,
                'completed_count': latest.completed_count if latest else 0,
                'blocked_count': latest.blocked_count if latest else 0,
                'rejected_count': latest.rejected_count if latest else 0,
                'closed_loop_count': latest.closed_loop_count if latest else 0,
                'recommendation_summary': latest.recommendation_summary if latest else {},
            },
            status=status.HTTP_200_OK,
        )


class AutonomyFeedbackCompleteView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, followup_id: int, *args, **kwargs):
        serializer = FeedbackActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        try:
            resolution = mark_resolution_complete(followup_id=followup_id, actor=serializer.validated_data['actor'])
        except CampaignFollowup.DoesNotExist:
            return Response({'detail': 'Follow-up not found.'}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as error:
            return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'resolution_id': resolution.id, 'resolution_status': resolution.resolution_status}, status=status.HTTP_200_OK)
