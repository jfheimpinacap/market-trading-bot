from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.autonomy_intake.models import PlanningProposal
from apps.autonomy_planning_review.models import PlanningProposalResolution, PlanningReviewRecommendation, PlanningReviewRun
from apps.autonomy_planning_review.serializers import (
    PlanningProposalResolutionSerializer,
    PlanningReviewActionSerializer,
    PlanningReviewRecommendationSerializer,
)
from apps.autonomy_planning_review.services import (
    acknowledge_proposal,
    build_planning_review_candidates,
    mark_accepted,
    mark_deferred,
    mark_rejected,
    run_planning_review,
)


class AutonomyPlanningReviewCandidatesView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = []
        for candidate in build_planning_review_candidates():
            rows.append(
                {
                    'planning_proposal': candidate.planning_proposal,
                    'backlog_item': candidate.backlog_item,
                    'advisory_artifact': candidate.advisory_artifact,
                    'insight': candidate.insight,
                    'campaign': candidate.campaign,
                    'campaign_title': candidate.campaign_title,
                    'proposal_type': candidate.proposal_type,
                    'proposal_status': candidate.proposal_status,
                    'target_scope': candidate.target_scope,
                    'downstream_status': candidate.downstream_status,
                    'ready_for_resolution': candidate.ready_for_resolution,
                    'blockers': candidate.blockers,
                    'metadata': candidate.metadata,
                }
            )
        return Response(rows, status=status.HTTP_200_OK)


class AutonomyPlanningReviewRunReviewView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = PlanningReviewActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        result = run_planning_review(actor=serializer.validated_data['actor'])
        return Response(
            {
                'run': result['run'].id,
                'candidate_count': len(result['candidates']),
                'resolution_count': len(result['resolutions']),
                'recommendation_count': len(result['recommendations']),
            },
            status=status.HTTP_200_OK,
        )


class AutonomyPlanningReviewResolutionListView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = PlanningProposalResolution.objects.select_related('planning_proposal', 'backlog_item', 'insight', 'campaign').order_by('-updated_at', '-id')[:500]
        return Response(PlanningProposalResolutionSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomyPlanningReviewResolutionDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, resolution_id: int, *args, **kwargs):
        try:
            row = PlanningProposalResolution.objects.select_related('planning_proposal', 'backlog_item', 'insight', 'campaign').get(pk=resolution_id)
        except PlanningProposalResolution.DoesNotExist:
            return Response({'detail': 'Planning proposal resolution not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(PlanningProposalResolutionSerializer(row).data, status=status.HTTP_200_OK)


class AutonomyPlanningReviewRecommendationListView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = PlanningReviewRecommendation.objects.select_related('planning_proposal', 'backlog_item').order_by('-created_at', '-id')[:500]
        return Response(PlanningReviewRecommendationSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomyPlanningReviewSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        latest = PlanningReviewRun.objects.order_by('-created_at', '-id').first()
        emitted_count = PlanningProposal.objects.filter(proposal_status='EMITTED').count()
        return Response(
            {
                'latest_run_id': latest.id if latest else None,
                'planning_proposals_emitted_count': emitted_count,
                'candidate_count': latest.candidate_count if latest else 0,
                'pending_count': latest.pending_count if latest else 0,
                'acknowledged_count': latest.acknowledged_count if latest else 0,
                'accepted_count': latest.accepted_count if latest else 0,
                'deferred_count': latest.deferred_count if latest else 0,
                'rejected_count': latest.rejected_count if latest else 0,
                'blocked_count': latest.blocked_count if latest else 0,
                'closed_count': latest.closed_count if latest else 0,
                'recommendation_summary': latest.recommendation_summary if latest else {},
            },
            status=status.HTTP_200_OK,
        )


class AutonomyPlanningReviewAcknowledgeView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, proposal_id: int, *args, **kwargs):
        serializer = PlanningReviewActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        try:
            resolution = acknowledge_proposal(proposal_id=proposal_id, actor=serializer.validated_data['actor'])
        except PlanningProposal.DoesNotExist:
            return Response({'detail': 'Planning proposal not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'resolution_id': resolution.id, 'resolution_status': resolution.resolution_status}, status=status.HTTP_200_OK)


class AutonomyPlanningReviewAcceptView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, proposal_id: int, *args, **kwargs):
        serializer = PlanningReviewActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        try:
            resolution = mark_accepted(
                proposal_id=proposal_id,
                actor=serializer.validated_data['actor'],
                rationale=serializer.validated_data.get('rationale'),
                reason_codes=serializer.validated_data.get('reason_codes'),
            )
        except PlanningProposal.DoesNotExist:
            return Response({'detail': 'Planning proposal not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'resolution_id': resolution.id, 'resolution_status': resolution.resolution_status}, status=status.HTTP_200_OK)


class AutonomyPlanningReviewDeferView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, proposal_id: int, *args, **kwargs):
        serializer = PlanningReviewActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        try:
            resolution = mark_deferred(
                proposal_id=proposal_id,
                actor=serializer.validated_data['actor'],
                rationale=serializer.validated_data.get('rationale'),
                reason_codes=serializer.validated_data.get('reason_codes'),
            )
        except PlanningProposal.DoesNotExist:
            return Response({'detail': 'Planning proposal not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'resolution_id': resolution.id, 'resolution_status': resolution.resolution_status}, status=status.HTTP_200_OK)


class AutonomyPlanningReviewRejectView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, proposal_id: int, *args, **kwargs):
        serializer = PlanningReviewActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        try:
            resolution = mark_rejected(
                proposal_id=proposal_id,
                actor=serializer.validated_data['actor'],
                rationale=serializer.validated_data.get('rationale'),
                reason_codes=serializer.validated_data.get('reason_codes'),
            )
        except PlanningProposal.DoesNotExist:
            return Response({'detail': 'Planning proposal not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'resolution_id': resolution.id, 'resolution_status': resolution.resolution_status}, status=status.HTTP_200_OK)
