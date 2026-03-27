from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.rollout_manager.models import StackRolloutPlan, StackRolloutRun
from apps.rollout_manager.serializers import (
    CreateRolloutPlanRequestSerializer,
    RolloutControlRequestSerializer,
    RolloutDecisionEvaluationRequestSerializer,
    StackRolloutPlanSerializer,
    StackRolloutRunSerializer,
    StartRolloutRunRequestSerializer,
)
from apps.rollout_manager.services import (
    build_rollout_summary,
    create_stack_rollout_plan,
    evaluate_guardrails,
    evaluate_rollout_decision,
    get_current_rollout_run,
    pause_rollout_run,
    resume_rollout_run,
    rollback_run,
    start_rollout_run,
)


class RolloutCreatePlanView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = CreateRolloutPlanRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        try:
            plan = create_stack_rollout_plan(payload=serializer.validated_data)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(StackRolloutPlanSerializer(plan).data, status=status.HTTP_201_CREATED)


class RolloutStartView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, pk: int, *args, **kwargs):
        serializer = StartRolloutRunRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        plan = get_object_or_404(StackRolloutPlan, pk=pk)
        run = start_rollout_run(plan=plan, metadata=serializer.validated_data.get('metadata') or {})
        return Response(StackRolloutRunSerializer(run).data, status=status.HTTP_201_CREATED)


class RolloutPauseView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, pk: int, *args, **kwargs):
        run = get_object_or_404(StackRolloutRun, pk=pk)
        run = pause_rollout_run(run=run)
        return Response(StackRolloutRunSerializer(run).data, status=status.HTTP_200_OK)


class RolloutResumeView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, pk: int, *args, **kwargs):
        run = get_object_or_404(StackRolloutRun, pk=pk)
        run = resume_rollout_run(run=run)
        return Response(StackRolloutRunSerializer(run).data, status=status.HTTP_200_OK)


class RolloutRollbackView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, pk: int, *args, **kwargs):
        serializer = RolloutControlRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        run = get_object_or_404(StackRolloutRun, pk=pk)
        reason = serializer.validated_data.get('reason') or 'Operator requested rollback.'
        run = rollback_run(run=run, reason=reason, actor=serializer.validated_data.get('actor', 'operator'))
        return Response(StackRolloutRunSerializer(run).data, status=status.HTTP_200_OK)


class RolloutEvaluateDecisionView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, pk: int, *args, **kwargs):
        serializer = RolloutDecisionEvaluationRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        run = get_object_or_404(StackRolloutRun, pk=pk)
        metrics = serializer.validated_data.get('metrics') or {}
        events = evaluate_guardrails(run=run, metrics=metrics)
        decision = evaluate_rollout_decision(run=run, metrics=metrics)
        return Response({'events_created': len(events), 'decision': decision.decision}, status=status.HTTP_200_OK)


class RolloutRunListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = StackRolloutRunSerializer

    def get_queryset(self):
        return StackRolloutRun.objects.select_related('plan__champion_binding', 'plan__candidate_binding').prefetch_related('guardrail_events', 'decisions').order_by('-created_at', '-id')[:80]


class RolloutRunDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = StackRolloutRunSerializer
    queryset = StackRolloutRun.objects.select_related('plan__champion_binding', 'plan__candidate_binding').prefetch_related('guardrail_events', 'decisions').order_by('-created_at', '-id')


class CurrentRolloutView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        run = get_current_rollout_run()
        return Response({'current_rollout': StackRolloutRunSerializer(run).data if run else None}, status=status.HTTP_200_OK)


class RolloutSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        summary = build_rollout_summary()
        return Response(
            {
                'current_run': StackRolloutRunSerializer(summary['current_run']).data if summary['current_run'] else None,
                'latest_run': StackRolloutRunSerializer(summary['latest_run']).data if summary['latest_run'] else None,
                'total_runs': summary['total_runs'],
                'running_count': summary['running_count'],
                'rolled_back_count': summary['rolled_back_count'],
                'last_updated_at': summary['last_updated_at'].isoformat(),
            },
            status=status.HTTP_200_OK,
        )
