from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.autonomy_backlog.models import GovernanceBacklogItem
from apps.autonomy_intake.models import IntakeRecommendation, IntakeRun, PlanningProposal
from apps.autonomy_intake.serializers import IntakeActionSerializer, IntakeRecommendationSerializer, PlanningProposalSerializer
from apps.autonomy_intake.services import acknowledge_proposal, build_intake_candidates, emit_proposal_for_backlog_item, run_intake_review


class AutonomyIntakeCandidatesView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = []
        for candidate in build_intake_candidates():
            rows.append(
                {
                    'backlog_item': candidate.backlog_item,
                    'advisory_artifact': candidate.advisory_artifact,
                    'insight': candidate.insight,
                    'campaign': candidate.campaign,
                    'campaign_title': candidate.campaign_title,
                    'backlog_type': candidate.backlog_type,
                    'target_scope': candidate.target_scope,
                    'priority_level': candidate.priority_level,
                    'ready_for_intake': candidate.ready_for_intake,
                    'existing_proposal': candidate.existing_proposal,
                    'blockers': candidate.blockers,
                    'metadata': candidate.metadata,
                }
            )
        return Response(rows, status=status.HTTP_200_OK)


class AutonomyIntakeRunReviewView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = IntakeActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        result = run_intake_review(actor=serializer.validated_data['actor'])
        return Response(
            {
                'run': result['run'].id,
                'candidate_count': len(result['candidates']),
                'emitted_count': len(result['emitted']),
                'recommendation_count': len(result['recommendations']),
            },
            status=status.HTTP_200_OK,
        )


class AutonomyIntakeProposalsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = PlanningProposal.objects.select_related('backlog_item', 'advisory_artifact', 'insight', 'campaign').order_by('-updated_at', '-id')[:500]
        return Response(PlanningProposalSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomyIntakeProposalDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, proposal_id: int, *args, **kwargs):
        try:
            proposal = PlanningProposal.objects.select_related('backlog_item', 'campaign').get(pk=proposal_id)
        except PlanningProposal.DoesNotExist:
            return Response({'detail': 'Planning proposal not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(PlanningProposalSerializer(proposal).data, status=status.HTTP_200_OK)


class AutonomyIntakeRecommendationsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = IntakeRecommendation.objects.select_related('backlog_item', 'proposal').order_by('-created_at', '-id')[:500]
        return Response(IntakeRecommendationSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomyIntakeSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        latest = IntakeRun.objects.order_by('-created_at', '-id').first()
        proposals = PlanningProposal.objects.all()
        return Response(
            {
                'latest_run_id': latest.id if latest else None,
                'candidate_count': latest.candidate_count if latest else 0,
                'ready_count': latest.ready_count if latest else 0,
                'blocked_count': latest.blocked_count if latest else 0,
                'emitted_count': latest.emitted_count if latest else 0,
                'duplicate_skipped_count': latest.duplicate_skipped_count if latest else 0,
                'roadmap_proposal_count': latest.roadmap_proposal_count if latest else 0,
                'scenario_proposal_count': latest.scenario_proposal_count if latest else 0,
                'program_proposal_count': latest.program_proposal_count if latest else 0,
                'manager_proposal_count': latest.manager_proposal_count if latest else 0,
                'recommendation_summary': latest.recommendation_summary if latest else {},
                'total_proposals': proposals.count(),
                'pending_review': proposals.filter(proposal_status='PENDING_REVIEW').count(),
                'ready': proposals.filter(proposal_status='READY').count(),
                'emitted': proposals.filter(proposal_status='EMITTED').count(),
                'acknowledged': proposals.filter(proposal_status='ACKNOWLEDGED').count(),
            },
            status=status.HTTP_200_OK,
        )


class AutonomyIntakeEmitView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, backlog_item_id: int, *args, **kwargs):
        serializer = IntakeActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        try:
            proposal = emit_proposal_for_backlog_item(backlog_item_id=backlog_item_id, actor=serializer.validated_data['actor'])
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except GovernanceBacklogItem.DoesNotExist:
            return Response({'detail': 'Backlog item not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'proposal_id': proposal.id, 'proposal_status': proposal.proposal_status}, status=status.HTTP_200_OK)


class AutonomyIntakeAcknowledgeView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, proposal_id: int, *args, **kwargs):
        serializer = IntakeActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        try:
            proposal = acknowledge_proposal(proposal_id=proposal_id, actor=serializer.validated_data['actor'])
        except PlanningProposal.DoesNotExist:
            return Response({'detail': 'Planning proposal not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'proposal_id': proposal.id, 'proposal_status': proposal.proposal_status}, status=status.HTTP_200_OK)
