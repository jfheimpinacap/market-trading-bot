from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.autonomy_advisory.models import AdvisoryArtifact
from apps.autonomy_advisory_resolution.models import AdvisoryResolution, AdvisoryResolutionRecommendation, AdvisoryResolutionRun
from apps.autonomy_advisory_resolution.serializers import (
    AdvisoryResolutionActionSerializer,
    AdvisoryResolutionRecommendationSerializer,
    AdvisoryResolutionSerializer,
)
from apps.autonomy_advisory_resolution.services import (
    acknowledge_artifact,
    build_advisory_resolution_candidates,
    mark_adopted,
    mark_deferred,
    mark_rejected,
    run_advisory_resolution_review,
)


class AutonomyAdvisoryResolutionCandidatesView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = []
        for candidate in build_advisory_resolution_candidates():
            rows.append(
                {
                    'advisory_artifact': candidate.advisory_artifact,
                    'insight': candidate.insight,
                    'campaign': candidate.campaign,
                    'campaign_title': candidate.campaign_title,
                    'artifact_type': candidate.artifact_type,
                    'artifact_status': candidate.artifact_status,
                    'target_scope': candidate.target_scope,
                    'downstream_status': candidate.downstream_status,
                    'ready_for_resolution': candidate.ready_for_resolution,
                    'blockers': candidate.blockers,
                    'metadata': candidate.metadata,
                }
            )
        return Response(rows, status=status.HTTP_200_OK)


class AutonomyAdvisoryResolutionRunReviewView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = AdvisoryResolutionActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        result = run_advisory_resolution_review(actor=serializer.validated_data['actor'])
        return Response(
            {
                'run': result['run'].id,
                'candidate_count': len(result['candidates']),
                'resolution_count': len(result['resolutions']),
                'recommendation_count': len(result['recommendations']),
            },
            status=status.HTTP_200_OK,
        )


class AutonomyAdvisoryResolutionListView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = AdvisoryResolution.objects.select_related('advisory_artifact', 'insight', 'campaign').order_by('-updated_at', '-id')[:500]
        return Response(AdvisoryResolutionSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomyAdvisoryResolutionRecommendationListView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = AdvisoryResolutionRecommendation.objects.select_related('advisory_artifact', 'insight').order_by('-created_at', '-id')[:500]
        return Response(AdvisoryResolutionRecommendationSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomyAdvisoryResolutionSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        latest = AdvisoryResolutionRun.objects.order_by('-created_at', '-id').first()
        emitted_count = AdvisoryArtifact.objects.filter(artifact_status='EMITTED').count()
        return Response(
            {
                'latest_run_id': latest.id if latest else None,
                'advisory_emitted_count': emitted_count,
                'candidate_count': latest.candidate_count if latest else 0,
                'pending_count': latest.pending_count if latest else 0,
                'acknowledged_count': latest.acknowledged_count if latest else 0,
                'adopted_count': latest.adopted_count if latest else 0,
                'deferred_count': latest.deferred_count if latest else 0,
                'rejected_count': latest.rejected_count if latest else 0,
                'blocked_count': latest.blocked_count if latest else 0,
                'closed_count': latest.closed_count if latest else 0,
                'recommendation_summary': latest.recommendation_summary if latest else {},
            },
            status=status.HTTP_200_OK,
        )


class AutonomyAdvisoryResolutionAcknowledgeView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, artifact_id: int, *args, **kwargs):
        serializer = AdvisoryResolutionActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        try:
            resolution = acknowledge_artifact(artifact_id=artifact_id, actor=serializer.validated_data['actor'])
        except AdvisoryArtifact.DoesNotExist:
            return Response({'detail': 'Advisory artifact not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'resolution_id': resolution.id, 'resolution_status': resolution.resolution_status}, status=status.HTTP_200_OK)


class AutonomyAdvisoryResolutionAdoptView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, artifact_id: int, *args, **kwargs):
        serializer = AdvisoryResolutionActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        try:
            resolution = mark_adopted(
                artifact_id=artifact_id,
                actor=serializer.validated_data['actor'],
                rationale=serializer.validated_data.get('rationale'),
                reason_codes=serializer.validated_data.get('reason_codes'),
            )
        except AdvisoryArtifact.DoesNotExist:
            return Response({'detail': 'Advisory artifact not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'resolution_id': resolution.id, 'resolution_status': resolution.resolution_status}, status=status.HTTP_200_OK)


class AutonomyAdvisoryResolutionDeferredView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, artifact_id: int, *args, **kwargs):
        serializer = AdvisoryResolutionActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        try:
            resolution = mark_deferred(
                artifact_id=artifact_id,
                actor=serializer.validated_data['actor'],
                rationale=serializer.validated_data.get('rationale'),
                reason_codes=serializer.validated_data.get('reason_codes'),
            )
        except AdvisoryArtifact.DoesNotExist:
            return Response({'detail': 'Advisory artifact not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'resolution_id': resolution.id, 'resolution_status': resolution.resolution_status}, status=status.HTTP_200_OK)


class AutonomyAdvisoryResolutionRejectView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, artifact_id: int, *args, **kwargs):
        serializer = AdvisoryResolutionActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        try:
            resolution = mark_rejected(
                artifact_id=artifact_id,
                actor=serializer.validated_data['actor'],
                rationale=serializer.validated_data.get('rationale'),
                reason_codes=serializer.validated_data.get('reason_codes'),
            )
        except AdvisoryArtifact.DoesNotExist:
            return Response({'detail': 'Advisory artifact not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'resolution_id': resolution.id, 'resolution_status': resolution.resolution_status}, status=status.HTTP_200_OK)
