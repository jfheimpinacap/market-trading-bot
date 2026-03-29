from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.autonomy_decision.models import DecisionRecommendation, DecisionRun, GovernanceDecision
from apps.autonomy_decision.serializers import DecisionActionSerializer, DecisionRecommendationSerializer, GovernanceDecisionSerializer
from apps.autonomy_decision.services import acknowledge_decision, build_decision_candidates, register_decision_for_proposal, run_decision_review
from apps.autonomy_planning_review.models import PlanningProposalResolution


class AutonomyDecisionCandidatesView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response([candidate.__dict__ for candidate in build_decision_candidates()], status=status.HTTP_200_OK)


class AutonomyDecisionRunReviewView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = DecisionActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        result = run_decision_review(actor=serializer.validated_data['actor'])
        return Response(
            {
                'run': result['run'].id,
                'candidate_count': len(result['candidates']),
                'recommendation_count': len(result['recommendations']),
            },
            status=status.HTTP_200_OK,
        )


class AutonomyDecisionListView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = GovernanceDecision.objects.select_related('planning_proposal', 'backlog_item', 'insight', 'campaign').order_by('-updated_at', '-id')[:500]
        return Response(GovernanceDecisionSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomyDecisionRecommendationListView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = DecisionRecommendation.objects.select_related('planning_proposal').order_by('-created_at', '-id')[:500]
        return Response(DecisionRecommendationSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomyDecisionSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        latest = DecisionRun.objects.order_by('-created_at', '-id').first()
        return Response(
            {
                'latest_run_id': latest.id if latest else None,
                'candidate_count': latest.candidate_count if latest else 0,
                'ready_count': latest.ready_count if latest else 0,
                'blocked_count': latest.blocked_count if latest else 0,
                'registered_count': latest.registered_count if latest else 0,
                'duplicate_skipped_count': latest.duplicate_skipped_count if latest else 0,
                'roadmap_decision_count': latest.roadmap_decision_count if latest else 0,
                'scenario_decision_count': latest.scenario_decision_count if latest else 0,
                'program_decision_count': latest.program_decision_count if latest else 0,
                'manager_decision_count': latest.manager_decision_count if latest else 0,
                'recommendation_summary': latest.recommendation_summary if latest else {},
            },
            status=status.HTTP_200_OK,
        )


class AutonomyDecisionRegisterView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, proposal_id: int, *args, **kwargs):
        serializer = DecisionActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        try:
            decision = register_decision_for_proposal(proposal_id=proposal_id, actor=serializer.validated_data['actor'])
        except GovernanceDecision.DoesNotExist:
            return Response({'detail': 'Planning proposal does not exist for decision registration.'}, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as err:
            return Response({'detail': str(err.message)}, status=status.HTTP_400_BAD_REQUEST)
        except PlanningProposalResolution.DoesNotExist:
            return Response({'detail': 'Planning proposal resolution not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'decision_id': decision.id, 'decision_status': decision.decision_status}, status=status.HTTP_200_OK)


class AutonomyDecisionAcknowledgeView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, decision_id: int, *args, **kwargs):
        try:
            decision = acknowledge_decision(decision_id=decision_id)
        except GovernanceDecision.DoesNotExist:
            return Response({'detail': 'Governance decision not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'decision_id': decision.id, 'decision_status': decision.decision_status}, status=status.HTTP_200_OK)
