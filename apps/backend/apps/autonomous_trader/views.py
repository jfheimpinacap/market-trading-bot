from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.autonomous_trader.models import (
    AutonomousDispatchRecord,
    AutonomousExecutionDecision,
    AutonomousExecutionIntakeCandidate,
    AutonomousExecutionIntakeRun,
    AutonomousExecutionRecommendation,
    AutonomousFeedbackCandidateContext,
    AutonomousFeedbackInfluenceRecord,
    AutonomousFeedbackRecommendation,
    AutonomousFeedbackReuseRun,
    AutonomousLearningHandoff,
    AutonomousOutcomeHandoffRecommendation,
    AutonomousOutcomeHandoffRun,
    AutonomousPostmortemHandoff,
    AutonomousSizingContext,
    AutonomousSizingDecision,
    AutonomousSizingRecommendation,
    AutonomousSizingRun,
    AutonomousPositionActionDecision,
    AutonomousPositionActionExecution,
    AutonomousPositionWatchCandidate,
    AutonomousPositionWatchRecommendation,
    AutonomousPositionWatchRun,
    AutonomousTradeCandidate,
    AutonomousTradeCycleRun,
    AutonomousTradeDecision,
    AutonomousTradeExecution,
    AutonomousTradeOutcome,
    AutonomousTradeWatchRecord,
)
from apps.autonomous_trader.serializers import (
    AutonomousDispatchRecordSerializer,
    AutonomousExecutionDecisionSerializer,
    AutonomousExecutionIntakeCandidateSerializer,
    AutonomousExecutionIntakeRunSerializer,
    AutonomousExecutionRecommendationSerializer,
    AutonomousFeedbackCandidateContextSerializer,
    AutonomousFeedbackInfluenceRecordSerializer,
    AutonomousFeedbackRecommendationSerializer,
    AutonomousFeedbackReuseRunSerializer,
    AutonomousLearningHandoffSerializer,
    AutonomousOutcomeHandoffRecommendationSerializer,
    AutonomousOutcomeHandoffRunSerializer,
    AutonomousPostmortemHandoffSerializer,
    AutonomousSizingContextSerializer,
    AutonomousSizingDecisionSerializer,
    AutonomousSizingRecommendationSerializer,
    AutonomousSizingRunSerializer,
    AutonomousPositionActionDecisionSerializer,
    AutonomousPositionActionExecutionSerializer,
    AutonomousPositionWatchCandidateSerializer,
    AutonomousPositionWatchRecommendationSerializer,
    AutonomousPositionWatchRunSerializer,
    AutonomousTradeCandidateSerializer,
    AutonomousTradeCycleRunSerializer,
    AutonomousTradeDecisionSerializer,
    AutonomousTradeExecutionSerializer,
    AutonomousTradeOutcomeSerializer,
    AutonomousTradeWatchRecordSerializer,
    RunExecutionIntakeSerializer,
    RunCycleSerializer,
    RunFeedbackReuseSerializer,
    RunSizingSerializer,
    RunPositionWatchSerializer,
    RunOutcomeHandoffSerializer,
)
from apps.autonomous_trader.services import (
    build_feedback_summary,
    build_outcome_handoff_summary,
    build_summary,
    run_autonomous_cycle,
    run_feedback_reuse_engine,
    run_outcome_handoff_engine,
)
from apps.autonomous_trader.services.execution_intake import build_execution_intake_summary, run_execution_intake
from apps.autonomous_trader.services.kelly_sizing import build_sizing_summary, run_sizing_bridge
from apps.autonomous_trader.services.position_watch import build_position_watch_summary, run_position_watch


class AutonomousTradeRunCycleView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RunCycleSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        result = run_autonomous_cycle(**serializer.validated_data)
        return Response({'run': result['run'].id, 'candidate_count': len(result['candidates'])}, status=status.HTTP_200_OK)


class AutonomousTradeRunExecutionIntakeView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RunExecutionIntakeSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        result = run_execution_intake(**serializer.validated_data)
        return Response({'run': result['run'].id, 'intake_candidate_count': len(result['intake_candidates'])}, status=status.HTTP_200_OK)


class AutonomousTradeRunWatchCycleView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RunCycleSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        data['cycle_mode'] = 'WATCH_ONLY'
        result = run_autonomous_cycle(**data)
        return Response({'run': result['run'].id, 'watch_records': len(result['watch_records'])}, status=status.HTTP_200_OK)


class AutonomousTradeRunOutcomeHandoffView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RunOutcomeHandoffSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        run = run_outcome_handoff_engine(**serializer.validated_data)
        return Response({'run': run.id}, status=status.HTTP_200_OK)


class AutonomousTradeRunFeedbackReuseView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RunFeedbackReuseSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        cycle_run = None
        if data.get('cycle_run_id'):
            cycle_run = get_object_or_404(AutonomousTradeCycleRun, pk=data['cycle_run_id'])
        run = run_feedback_reuse_engine(cycle_run=cycle_run, actor=data.get('actor') or 'operator-ui', limit=data.get('limit', 25))
        return Response({'run': run.id}, status=status.HTTP_200_OK)


class AutonomousTradeRunSizingView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RunSizingSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        result = run_sizing_bridge(**serializer.validated_data)
        return Response({'run': result['run'].id, 'decision_count': len(result['decisions'])}, status=status.HTTP_200_OK)


class AutonomousTradeCyclesView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = AutonomousTradeCycleRun.objects.order_by('-started_at', '-id')[:100]
        return Response(AutonomousTradeCycleRunSerializer(rows, many=True).data)


class AutonomousTradeCycleDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, cycle_id: int, *args, **kwargs):
        row = get_object_or_404(AutonomousTradeCycleRun, pk=cycle_id)
        return Response(AutonomousTradeCycleRunSerializer(row).data)


class AutonomousTradeCandidatesView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = AutonomousTradeCandidate.objects.select_related('linked_market').order_by('-created_at', '-id')[:200]
        return Response(AutonomousTradeCandidateSerializer(rows, many=True).data)


class AutonomousTradeDecisionsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = AutonomousTradeDecision.objects.select_related('linked_candidate__linked_market').order_by('-created_at', '-id')[:200]
        return Response(AutonomousTradeDecisionSerializer(rows, many=True).data)


class AutonomousTradeExecutionsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = AutonomousTradeExecution.objects.select_related('linked_candidate__linked_market', 'linked_paper_trade').order_by('-created_at', '-id')[:200]
        return Response(AutonomousTradeExecutionSerializer(rows, many=True).data)


class AutonomousTradeWatchRecordsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = AutonomousTradeWatchRecord.objects.select_related('linked_execution__linked_candidate__linked_market').order_by('-created_at', '-id')[:200]
        return Response(AutonomousTradeWatchRecordSerializer(rows, many=True).data)


class AutonomousTradeOutcomesView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = AutonomousTradeOutcome.objects.select_related('linked_execution__linked_candidate__linked_market').order_by('-created_at', '-id')[:200]
        return Response(AutonomousTradeOutcomeSerializer(rows, many=True).data)


class AutonomousTradeSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(build_summary())


class AutonomousExecutionIntakeRunsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = AutonomousExecutionIntakeRun.objects.order_by('-started_at', '-id')[:100]
        return Response(AutonomousExecutionIntakeRunSerializer(rows, many=True).data)


class AutonomousExecutionIntakeCandidatesView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = AutonomousExecutionIntakeCandidate.objects.select_related('linked_market').order_by('-created_at', '-id')[:200]
        return Response(AutonomousExecutionIntakeCandidateSerializer(rows, many=True).data)


class AutonomousExecutionIntakeCandidateDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, candidate_id: int, *args, **kwargs):
        row = get_object_or_404(AutonomousExecutionIntakeCandidate, pk=candidate_id)
        return Response(AutonomousExecutionIntakeCandidateSerializer(row).data)


class AutonomousExecutionDecisionsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = AutonomousExecutionDecision.objects.select_related('linked_intake_candidate__linked_market').order_by('-created_at', '-id')[:200]
        return Response(AutonomousExecutionDecisionSerializer(rows, many=True).data)


class AutonomousExecutionDecisionDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, decision_id: int, *args, **kwargs):
        row = get_object_or_404(AutonomousExecutionDecision, pk=decision_id)
        return Response(AutonomousExecutionDecisionSerializer(row).data)


class AutonomousDispatchRecordsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = AutonomousDispatchRecord.objects.select_related('linked_execution_decision__linked_intake_candidate__linked_market').order_by('-created_at', '-id')[:200]
        return Response(AutonomousDispatchRecordSerializer(rows, many=True).data)


class AutonomousExecutionRecommendationsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = AutonomousExecutionRecommendation.objects.select_related('target_market').order_by('-created_at', '-id')[:200]
        return Response(AutonomousExecutionRecommendationSerializer(rows, many=True).data)


class AutonomousExecutionIntakeSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(build_execution_intake_summary())


class AutonomousOutcomeHandoffRunsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = AutonomousOutcomeHandoffRun.objects.order_by('-started_at', '-id')[:100]
        return Response(AutonomousOutcomeHandoffRunSerializer(rows, many=True).data)


class AutonomousPostmortemHandoffsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = AutonomousPostmortemHandoff.objects.select_related('linked_outcome', 'linked_postmortem_run').order_by('-created_at', '-id')[:200]
        return Response(AutonomousPostmortemHandoffSerializer(rows, many=True).data)


class AutonomousLearningHandoffsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = AutonomousLearningHandoff.objects.select_related('linked_outcome', 'linked_learning_run').order_by('-created_at', '-id')[:200]
        return Response(AutonomousLearningHandoffSerializer(rows, many=True).data)


class AutonomousOutcomeHandoffRecommendationsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = AutonomousOutcomeHandoffRecommendation.objects.select_related('target_outcome').order_by('-created_at', '-id')[:200]
        return Response(AutonomousOutcomeHandoffRecommendationSerializer(rows, many=True).data)


class AutonomousOutcomeHandoffSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(build_outcome_handoff_summary())


class AutonomousFeedbackReuseRunsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = AutonomousFeedbackReuseRun.objects.order_by('-started_at', '-id')[:100]
        return Response(AutonomousFeedbackReuseRunSerializer(rows, many=True).data)


class AutonomousFeedbackCandidateContextsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = AutonomousFeedbackCandidateContext.objects.select_related('linked_market', 'linked_candidate').order_by('-created_at', '-id')[:200]
        return Response(AutonomousFeedbackCandidateContextSerializer(rows, many=True).data)


class AutonomousFeedbackInfluencesView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = AutonomousFeedbackInfluenceRecord.objects.select_related('linked_candidate__linked_market', 'linked_candidate_context').order_by('-created_at', '-id')[:200]
        return Response(AutonomousFeedbackInfluenceRecordSerializer(rows, many=True).data)


class AutonomousFeedbackRecommendationsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = AutonomousFeedbackRecommendation.objects.select_related('target_candidate').order_by('-created_at', '-id')[:200]
        return Response(AutonomousFeedbackRecommendationSerializer(rows, many=True).data)


class AutonomousFeedbackSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(build_feedback_summary())


class AutonomousPositionWatchRunView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RunPositionWatchSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        result = run_position_watch(**serializer.validated_data)
        return Response({'run': result['run'].id, 'considered': len(result['candidates'])}, status=status.HTTP_200_OK)


class AutonomousPositionWatchRunsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = AutonomousPositionWatchRun.objects.order_by('-started_at', '-id')[:100]
        return Response(AutonomousPositionWatchRunSerializer(rows, many=True).data)


class AutonomousPositionWatchCandidatesView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = AutonomousPositionWatchCandidate.objects.select_related('linked_market', 'linked_position').order_by('-created_at', '-id')[:200]
        return Response(AutonomousPositionWatchCandidateSerializer(rows, many=True).data)


class AutonomousPositionActionDecisionsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = AutonomousPositionActionDecision.objects.select_related('linked_watch_candidate__linked_market').order_by('-created_at', '-id')[:200]
        return Response(AutonomousPositionActionDecisionSerializer(rows, many=True).data)


class AutonomousPositionActionExecutionsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = AutonomousPositionActionExecution.objects.select_related('linked_position__market', 'linked_paper_trade').order_by('-created_at', '-id')[:200]
        return Response(AutonomousPositionActionExecutionSerializer(rows, many=True).data)


class AutonomousPositionWatchRecommendationsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = AutonomousPositionWatchRecommendation.objects.select_related('target_position__market').order_by('-created_at', '-id')[:200]
        return Response(AutonomousPositionWatchRecommendationSerializer(rows, many=True).data)


class AutonomousPositionWatchSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(build_position_watch_summary())


class AutonomousSizingRunsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = AutonomousSizingRun.objects.order_by('-started_at', '-id')[:100]
        return Response(AutonomousSizingRunSerializer(rows, many=True).data)


class AutonomousSizingContextsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = AutonomousSizingContext.objects.select_related('linked_candidate__linked_market').order_by('-created_at', '-id')[:200]
        return Response(AutonomousSizingContextSerializer(rows, many=True).data)


class AutonomousSizingDecisionsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = AutonomousSizingDecision.objects.select_related('linked_candidate__linked_market').order_by('-created_at', '-id')[:200]
        return Response(AutonomousSizingDecisionSerializer(rows, many=True).data)


class AutonomousSizingRecommendationsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = AutonomousSizingRecommendation.objects.select_related('target_candidate__linked_market').order_by('-created_at', '-id')[:200]
        return Response(AutonomousSizingRecommendationSerializer(rows, many=True).data)


class AutonomousSizingSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(build_sizing_summary())
