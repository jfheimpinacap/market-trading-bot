from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.policy_rollout.models import PolicyRolloutRun
from apps.policy_rollout.serializers import (
    PolicyRolloutRunSerializer,
    RollbackPolicyRolloutSerializer,
    RolloutEvaluationSerializer,
    StartPolicyRolloutSerializer,
)
from apps.policy_rollout.services import apply_manual_rollback, build_rollout_summary, capture_post_change_snapshot, create_rollout_run, evaluate_rollout
from apps.policy_tuning.models import PolicyTuningApplicationLog, PolicyTuningCandidate, PolicyTuningCandidateStatus


class StartPolicyRolloutView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = StartPolicyRolloutSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)

        candidate = get_object_or_404(PolicyTuningCandidate, pk=serializer.validated_data['policy_tuning_candidate_id'])
        if candidate.status != PolicyTuningCandidateStatus.APPLIED:
            return Response({'detail': 'Policy rollout can only start from APPLIED policy tuning candidates.'}, status=status.HTTP_400_BAD_REQUEST)

        application_log_id = serializer.validated_data.get('application_log_id')
        if application_log_id:
            application_log = get_object_or_404(PolicyTuningApplicationLog, pk=application_log_id, candidate=candidate)
        else:
            application_log = candidate.application_logs.order_by('-applied_at', '-id').first()

        if not application_log:
            return Response({'detail': 'Applied candidate does not have a policy tuning application log.'}, status=status.HTTP_400_BAD_REQUEST)

        run = create_rollout_run(
            candidate=candidate,
            application_log=application_log,
            observation_window_days=serializer.validated_data.get('observation_window_days', 14),
            metadata=serializer.validated_data.get('metadata') or {},
        )
        return Response(PolicyRolloutRunSerializer(run).data, status=status.HTTP_201_CREATED)


class PolicyRolloutRunListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PolicyRolloutRunSerializer

    def get_queryset(self):
        return PolicyRolloutRun.objects.select_related(
            'policy_tuning_candidate',
            'application_log',
            'baseline_snapshot',
            'post_change_snapshot',
        ).prefetch_related('recommendations').order_by('-created_at', '-id')[:100]


class PolicyRolloutRunDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PolicyRolloutRunSerializer
    queryset = PolicyRolloutRun.objects.select_related(
        'policy_tuning_candidate',
        'application_log',
        'baseline_snapshot',
        'post_change_snapshot',
    ).prefetch_related('recommendations').order_by('-created_at', '-id')


class EvaluatePolicyRolloutView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, pk: int, *args, **kwargs):
        serializer = RolloutEvaluationSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        run = get_object_or_404(PolicyRolloutRun, pk=pk)
        snapshot = capture_post_change_snapshot(run)
        recommendation = evaluate_rollout(run)
        run.refresh_from_db()
        return Response(
            {
                'run': PolicyRolloutRunSerializer(run).data,
                'post_change_snapshot_id': snapshot.id,
                'recommendation': recommendation.recommendation,
            },
            status=status.HTTP_200_OK,
        )


class RollbackPolicyRolloutView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, pk: int, *args, **kwargs):
        serializer = RollbackPolicyRolloutSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        run = get_object_or_404(PolicyRolloutRun, pk=pk)
        try:
            outcome = apply_manual_rollback(
                run=run,
                reason=serializer.validated_data['reason'],
                require_approval=serializer.validated_data.get('require_approval', True),
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        run.refresh_from_db()
        return Response({'run': PolicyRolloutRunSerializer(run).data, 'rollback_outcome': outcome}, status=status.HTTP_200_OK)


class PolicyRolloutSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(build_rollout_summary(), status=status.HTTP_200_OK)
