from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.autonomy_advisory.models import AdvisoryArtifact, AdvisoryRecommendation, AdvisoryRun
from apps.autonomy_advisory.serializers import AdvisoryActionSerializer, AdvisoryArtifactSerializer, AdvisoryRecommendationSerializer
from apps.autonomy_advisory.services import build_advisory_candidates, emit_advisory_for_insight, run_advisory_review
from apps.autonomy_insights.models import CampaignInsight


class AutonomyAdvisoryCandidatesView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = []
        for candidate in build_advisory_candidates():
            rows.append(
                {
                    'insight': candidate.insight_id,
                    'campaign': candidate.campaign_id,
                    'campaign_title': candidate.campaign_title,
                    'insight_type': candidate.insight_type,
                    'recommendation_target': candidate.recommendation_target,
                    'recommendation_type': candidate.recommendation_type,
                    'review_status': candidate.review_status,
                    'ready_for_emission': candidate.ready_for_emission,
                    'existing_artifact': candidate.existing_artifact,
                    'blockers': candidate.blockers,
                    'metadata': candidate.metadata,
                }
            )
        return Response(rows, status=status.HTTP_200_OK)


class AutonomyAdvisoryRunReviewView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = AdvisoryActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        result = run_advisory_review(actor=serializer.validated_data['actor'])
        return Response(
            {
                'run': result['run'].id,
                'candidate_count': len(result['candidates']),
                'recommendation_count': len(result['recommendations']),
                'emitted_count': len(result['emitted_artifacts']),
            },
            status=status.HTTP_200_OK,
        )


class AutonomyAdvisoryArtifactListView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = AdvisoryArtifact.objects.select_related('insight', 'campaign', 'linked_memory_document').order_by('-created_at', '-id')[:500]
        return Response(AdvisoryArtifactSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomyAdvisoryRecommendationListView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = AdvisoryRecommendation.objects.select_related('campaign_insight', 'target_campaign').order_by('-created_at', '-id')[:500]
        return Response(AdvisoryRecommendationSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomyAdvisorySummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        latest = AdvisoryRun.objects.order_by('-created_at', '-id').first()
        return Response(
            {
                'latest_run_id': latest.id if latest else None,
                'candidate_count': latest.candidate_count if latest else 0,
                'ready_count': latest.ready_count if latest else 0,
                'blocked_count': latest.blocked_count if latest else 0,
                'emitted_count': latest.emitted_count if latest else 0,
                'duplicate_skipped_count': latest.duplicate_skipped_count if latest else 0,
                'memory_note_count': latest.memory_note_count if latest else 0,
                'roadmap_note_count': latest.roadmap_note_count if latest else 0,
                'scenario_note_count': latest.scenario_note_count if latest else 0,
                'program_note_count': latest.program_note_count if latest else 0,
                'manager_note_count': latest.manager_note_count if latest else 0,
                'recommendation_summary': latest.recommendation_summary if latest else {},
            },
            status=status.HTTP_200_OK,
        )


class AutonomyAdvisoryEmitView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, insight_id: int, *args, **kwargs):
        serializer = AdvisoryActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        try:
            artifact = emit_advisory_for_insight(insight_id=insight_id, actor=serializer.validated_data['actor'])
        except CampaignInsight.DoesNotExist:
            return Response({'detail': 'Insight not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'artifact_id': artifact.id, 'artifact_status': artifact.artifact_status}, status=status.HTTP_200_OK)
