from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.autonomy_advisory_resolution.models import AdvisoryResolution
from apps.autonomy_backlog.models import BacklogRecommendation, BacklogRun, GovernanceBacklogItem
from apps.autonomy_backlog.serializers import BacklogActionSerializer, BacklogRecommendationSerializer, GovernanceBacklogItemSerializer
from apps.autonomy_backlog.services import build_backlog_candidates, create_backlog_item, mark_deferred, mark_prioritized, run_backlog_review


class AutonomyBacklogCandidatesView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = []
        for candidate in build_backlog_candidates():
            rows.append(
                {
                    'advisory_artifact': candidate.advisory_artifact,
                    'advisory_resolution': candidate.advisory_resolution,
                    'insight': candidate.insight,
                    'campaign': candidate.campaign,
                    'campaign_title': candidate.campaign_title,
                    'target_scope': candidate.target_scope,
                    'resolution_status': candidate.resolution_status,
                    'ready_for_backlog': candidate.ready_for_backlog,
                    'existing_backlog_item': candidate.existing_backlog_item,
                    'blockers': candidate.blockers,
                    'metadata': candidate.metadata,
                }
            )
        return Response(rows, status=status.HTTP_200_OK)


class AutonomyBacklogRunReviewView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = BacklogActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        result = run_backlog_review(actor=serializer.validated_data['actor'])
        return Response(
            {
                'run': result['run'].id,
                'candidate_count': len(result['candidates']),
                'created_count': len(result['created_items']),
                'recommendation_count': len(result['recommendations']),
            },
            status=status.HTTP_200_OK,
        )


class AutonomyBacklogItemsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = GovernanceBacklogItem.objects.select_related('advisory_artifact', 'advisory_resolution', 'insight', 'campaign').order_by('-updated_at', '-id')[:500]
        return Response(GovernanceBacklogItemSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomyBacklogRecommendationsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = BacklogRecommendation.objects.select_related('advisory_artifact', 'insight', 'backlog_item').order_by('-created_at', '-id')[:500]
        return Response(BacklogRecommendationSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomyBacklogSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        latest = BacklogRun.objects.order_by('-created_at', '-id').first()
        items = GovernanceBacklogItem.objects.all()
        return Response(
            {
                'latest_run_id': latest.id if latest else None,
                'candidate_count': latest.candidate_count if latest else 0,
                'ready_count': latest.ready_count if latest else 0,
                'blocked_count': latest.blocked_count if latest else 0,
                'created_count': latest.created_count if latest else 0,
                'duplicate_skipped_count': latest.duplicate_skipped_count if latest else 0,
                'prioritized_count': latest.prioritized_count if latest else 0,
                'recommendation_summary': latest.recommendation_summary if latest else {},
                'total_items': items.count(),
                'critical_items': items.filter(priority_level='CRITICAL').count(),
                'prioritized_items': items.filter(backlog_status='PRIORITIZED').count(),
                'deferred_items': items.filter(backlog_status='DEFERRED').count(),
            },
            status=status.HTTP_200_OK,
        )


class AutonomyBacklogCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, artifact_id: int, *args, **kwargs):
        serializer = BacklogActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        try:
            item = create_backlog_item(artifact_id=artifact_id, actor=serializer.validated_data['actor'])
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except AdvisoryResolution.DoesNotExist:
            return Response({'detail': 'Advisory resolution not found for artifact.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'item_id': item.id, 'backlog_status': item.backlog_status}, status=status.HTTP_200_OK)


class AutonomyBacklogPrioritizeView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, item_id: int, *args, **kwargs):
        serializer = BacklogActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        try:
            item = mark_prioritized(item_id=item_id, actor=serializer.validated_data['actor'])
        except GovernanceBacklogItem.DoesNotExist:
            return Response({'detail': 'Backlog item not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'item_id': item.id, 'backlog_status': item.backlog_status}, status=status.HTTP_200_OK)


class AutonomyBacklogDeferView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, item_id: int, *args, **kwargs):
        serializer = BacklogActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        try:
            item = mark_deferred(item_id=item_id, actor=serializer.validated_data['actor'])
        except GovernanceBacklogItem.DoesNotExist:
            return Response({'detail': 'Backlog item not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'item_id': item.id, 'backlog_status': item.backlog_status}, status=status.HTTP_200_OK)
