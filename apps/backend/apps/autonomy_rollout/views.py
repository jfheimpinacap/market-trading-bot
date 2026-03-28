from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.autonomy_manager.models import AutonomyStageTransition, AutonomyTransitionStatus
from apps.autonomy_rollout.models import AutonomyRolloutRun
from apps.autonomy_rollout.serializers import (
    AutonomyRolloutRunSerializer,
    RollbackAutonomyRolloutSerializer,
    RolloutEvaluationSerializer,
    StartAutonomyRolloutSerializer,
)
from apps.autonomy_rollout.services import apply_manual_rollback, build_rollout_summary, capture_post_change_snapshot, create_rollout_run, evaluate_rollout


class StartAutonomyRolloutView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = StartAutonomyRolloutSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)

        transition = get_object_or_404(AutonomyStageTransition.objects.select_related('domain', 'state'), pk=serializer.validated_data['autonomy_stage_transition_id'])
        if transition.status != AutonomyTransitionStatus.APPLIED:
            return Response({'detail': 'Autonomy rollout can only start from APPLIED domain stage transitions.'}, status=status.HTTP_400_BAD_REQUEST)

        run = create_rollout_run(
            transition=transition,
            observation_window_days=serializer.validated_data.get('observation_window_days', 14),
            metadata=serializer.validated_data.get('metadata') or {},
        )
        return Response(AutonomyRolloutRunSerializer(run).data, status=status.HTTP_201_CREATED)


class AutonomyRolloutRunListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = AutonomyRolloutRunSerializer

    def get_queryset(self):
        return AutonomyRolloutRun.objects.select_related(
            'autonomy_stage_transition',
            'domain',
            'baseline_snapshot',
            'post_change_snapshot',
        ).prefetch_related('recommendations').order_by('-created_at', '-id')[:100]


class AutonomyRolloutRunDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = AutonomyRolloutRunSerializer
    queryset = AutonomyRolloutRun.objects.select_related(
        'autonomy_stage_transition',
        'domain',
        'baseline_snapshot',
        'post_change_snapshot',
    ).prefetch_related('recommendations').order_by('-created_at', '-id')


class EvaluateAutonomyRolloutView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, pk: int, *args, **kwargs):
        serializer = RolloutEvaluationSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        run = get_object_or_404(AutonomyRolloutRun, pk=pk)
        snapshot = capture_post_change_snapshot(run)
        recommendation = evaluate_rollout(run)
        run.refresh_from_db()
        return Response(
            {
                'run': AutonomyRolloutRunSerializer(run).data,
                'post_change_snapshot_id': snapshot.id,
                'recommendation': recommendation.recommendation,
            },
            status=status.HTTP_200_OK,
        )


class RollbackAutonomyRolloutView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, pk: int, *args, **kwargs):
        serializer = RollbackAutonomyRolloutSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        run = get_object_or_404(AutonomyRolloutRun, pk=pk)
        try:
            outcome = apply_manual_rollback(
                run=run,
                reason=serializer.validated_data['reason'],
                require_approval=serializer.validated_data.get('require_approval', True),
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        run.refresh_from_db()
        return Response({'run': AutonomyRolloutRunSerializer(run).data, 'rollback_outcome': outcome}, status=status.HTTP_200_OK)


class AutonomyRolloutSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(build_rollout_summary(), status=status.HTTP_200_OK)
