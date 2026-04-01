from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.autonomous_trader.models import (
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
    AutonomousTradeCandidate,
    AutonomousTradeCycleRun,
    AutonomousTradeDecision,
    AutonomousTradeExecution,
    AutonomousTradeOutcome,
    AutonomousTradeWatchRecord,
)
from apps.autonomous_trader.serializers import (
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
    AutonomousTradeCandidateSerializer,
    AutonomousTradeCycleRunSerializer,
    AutonomousTradeDecisionSerializer,
    AutonomousTradeExecutionSerializer,
    AutonomousTradeOutcomeSerializer,
    AutonomousTradeWatchRecordSerializer,
    RunCycleSerializer,
    RunFeedbackReuseSerializer,
    RunSizingSerializer,
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
from apps.autonomous_trader.services.kelly_sizing import build_sizing_summary, run_sizing_bridge


class AutonomousTradeRunCycleView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RunCycleSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        result = run_autonomous_cycle(**serializer.validated_data)
        return Response({'run': result['run'].id, 'candidate_count': len(result['candidates'])}, status=status.HTTP_200_OK)


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
