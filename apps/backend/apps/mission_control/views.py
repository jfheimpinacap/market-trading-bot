from rest_framework import generics, status
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.mission_control.models import (
    AutonomousCadenceDecision,
    AutonomousHeartbeatDecision,
    AutonomousHeartbeatRecommendation,
    AutonomousHeartbeatRun,
    AutonomousMissionCycleExecution,
    AutonomousMissionCycleOutcome,
    AutonomousMissionCyclePlan,
    AutonomousMissionRuntimeRecommendation,
    AutonomousMissionRuntimeRun,
    AutonomousRunnerState,
    AutonomousRuntimeSession,
    AutonomousRuntimeTick,
    AutonomousProfileRecommendation,
    AutonomousProfileSelectionRun,
    AutonomousProfileSwitchDecision,
    AutonomousProfileSwitchRecord,
    AutonomousSessionContextReview,
    AutonomousScheduleProfile,
    AutonomousSessionTimingSnapshot,
    AutonomousStopConditionEvaluation,
    AutonomousSessionRecommendation,
    AutonomousTimingDecision,
    AutonomousTimingRecommendation,
    AutonomousTickDispatchAttempt,
    MissionControlCycle,
    MissionControlSession,
)
from apps.mission_control.serializers import (
    AutonomousCadenceDecisionSerializer,
    AutonomousCycleExecutionSerializer,
    AutonomousCycleOutcomeSerializer,
    AutonomousCyclePlanSerializer,
    AutonomousHeartbeatDecisionSerializer,
    AutonomousHeartbeatRecommendationSerializer,
    AutonomousHeartbeatRunSerializer,
    AutonomousRunnerStateSerializer,
    AutonomousRuntimeSessionSerializer,
    AutonomousRuntimeTickSerializer,
    AutonomousProfileRecommendationSerializer,
    AutonomousProfileSelectionRunSerializer,
    AutonomousProfileSwitchDecisionSerializer,
    AutonomousProfileSwitchRecordSerializer,
    AutonomousSessionContextReviewSerializer,
    AutonomousScheduleProfileSerializer,
    AutonomousSessionTimingSnapshotSerializer,
    AutonomousStopConditionEvaluationSerializer,
    AutonomousRuntimeRecommendationSerializer,
    AutonomousRuntimeRunRequestSerializer,
    AutonomousRuntimeRunSerializer,
    AutonomousTimingDecisionSerializer,
    AutonomousTimingRecommendationSerializer,
    SessionTimingReviewRequestSerializer,
    ProfileSelectionReviewRequestSerializer,
    AutonomousSessionRecommendationSerializer,
    AutonomousSessionStartRequestSerializer,
    AutonomousTickDispatchAttemptSerializer,
    MissionControlCycleSerializer,
    MissionControlSessionSerializer,
    MissionControlStartSerializer,
)
from apps.mission_control.services.session_timing import (
    apply_schedule_profile,
    build_session_timing_summary,
    ensure_default_schedule_profiles,
    run_session_timing_review,
)
from apps.mission_control.services import pause_session, resume_session, run_cycle_now, start_session, status_snapshot, stop_session
from apps.mission_control.services.autonomous_runtime import build_autonomous_runtime_summary, run_autonomous_runtime
from apps.mission_control.services.session_runtime import (
    build_session_summary,
    pause_session as pause_autonomous_session,
    resume_session as resume_autonomous_session,
    run_tick,
    start_session as start_autonomous_session,
    stop_session as stop_autonomous_session,
)
from apps.mission_control.services.session_heartbeat import (
    build_heartbeat_summary,
    get_runner_state,
    pause_runner,
    resume_runner,
    run_heartbeat_pass,
    start_runner,
    stop_runner,
)
from apps.mission_control.services.session_profile_control import (
    build_profile_selection_summary,
    run_profile_selection_review,
)
from apps.mission_control.services.session_profile_control.profile_switch import apply_profile_switch_decision


class MissionControlStatusView(APIView):
    def get(self, request, *args, **kwargs):
        return Response(status_snapshot(), status=status.HTTP_200_OK)


class MissionControlStartView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = MissionControlStartSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        profile_slug = payload.pop('profile_slug', None)
        session = start_session(profile_slug=profile_slug, overrides=payload)
        return Response(MissionControlSessionSerializer(session).data, status=status.HTTP_200_OK)


class MissionControlPauseView(APIView):
    def post(self, request, *args, **kwargs):
        session = pause_session()
        return Response(MissionControlSessionSerializer(session).data, status=status.HTTP_200_OK)


class MissionControlResumeView(APIView):
    def post(self, request, *args, **kwargs):
        session = resume_session()
        return Response(MissionControlSessionSerializer(session).data, status=status.HTTP_200_OK)


class MissionControlStopView(APIView):
    def post(self, request, *args, **kwargs):
        session = stop_session()
        return Response(MissionControlSessionSerializer(session).data if session else {'status': 'STOPPED'}, status=status.HTTP_200_OK)


class MissionControlRunCycleView(APIView):
    def post(self, request, *args, **kwargs):
        cycle = run_cycle_now(profile_slug=request.data.get('profile_slug'))
        return Response(MissionControlCycleSerializer(cycle).data, status=status.HTTP_200_OK)


class MissionControlSessionListView(generics.ListAPIView):
    serializer_class = MissionControlSessionSerializer

    def get_queryset(self):
        return MissionControlSession.objects.order_by('-started_at', '-id')[:50]


class MissionControlSessionDetailView(generics.RetrieveAPIView):
    serializer_class = MissionControlSessionSerializer
    queryset = MissionControlSession.objects.order_by('-started_at', '-id')


class MissionControlCycleListView(generics.ListAPIView):
    serializer_class = MissionControlCycleSerializer

    def get_queryset(self):
        return MissionControlCycle.objects.select_related('session').prefetch_related('steps').order_by('-started_at', '-id')[:80]


class MissionControlCycleDetailView(generics.RetrieveAPIView):
    serializer_class = MissionControlCycleSerializer
    queryset = MissionControlCycle.objects.select_related('session').prefetch_related('steps').order_by('-started_at', '-id')


class MissionControlSummaryView(APIView):
    def get(self, request, *args, **kwargs):
        latest_session = MissionControlSession.objects.order_by('-started_at').first()
        latest_cycle = MissionControlCycle.objects.order_by('-started_at').first()
        return Response({
            'latest_session': MissionControlSessionSerializer(latest_session).data if latest_session else None,
            'latest_cycle': MissionControlCycleSerializer(latest_cycle).data if latest_cycle else None,
            'session_count': MissionControlSession.objects.count(),
            'cycle_count': MissionControlCycle.objects.count(),
        }, status=status.HTTP_200_OK)


class RunAutonomousRuntimeView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = AutonomousRuntimeRunRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        runtime_run = run_autonomous_runtime(**serializer.validated_data)
        return Response(AutonomousRuntimeRunSerializer(runtime_run).data, status=status.HTTP_200_OK)


class AutonomousRuntimeRunListView(generics.ListAPIView):
    serializer_class = AutonomousRuntimeRunSerializer
    queryset = AutonomousMissionRuntimeRun.objects.order_by('-started_at', '-id')[:50]


class AutonomousCyclePlanListView(generics.ListAPIView):
    serializer_class = AutonomousCyclePlanSerializer
    queryset = AutonomousMissionCyclePlan.objects.select_related('linked_runtime_run').order_by('-created_at', '-id')[:100]


class AutonomousCycleExecutionListView(generics.ListAPIView):
    serializer_class = AutonomousCycleExecutionSerializer
    queryset = AutonomousMissionCycleExecution.objects.select_related('linked_cycle_plan').order_by('-created_at', '-id')[:100]


class AutonomousCycleOutcomeListView(generics.ListAPIView):
    serializer_class = AutonomousCycleOutcomeSerializer
    queryset = AutonomousMissionCycleOutcome.objects.select_related('linked_cycle_execution').order_by('-created_at', '-id')[:100]


class AutonomousRuntimeRecommendationListView(generics.ListAPIView):
    serializer_class = AutonomousRuntimeRecommendationSerializer
    queryset = AutonomousMissionRuntimeRecommendation.objects.order_by('-created_at', '-id')[:100]


class AutonomousRuntimeSummaryView(APIView):
    def get(self, request, *args, **kwargs):
        return Response(build_autonomous_runtime_summary(), status=status.HTTP_200_OK)


class StartAutonomousSessionView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = AutonomousSessionStartRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        session = start_autonomous_session(profile_slug=payload.get('profile_slug'), runtime_mode=payload.get('runtime_mode'))
        return Response(AutonomousRuntimeSessionSerializer(session).data, status=status.HTTP_200_OK)


class PauseAutonomousSessionView(APIView):
    def post(self, request, session_id: int, *args, **kwargs):
        session = pause_autonomous_session(session_id=session_id)
        return Response(AutonomousRuntimeSessionSerializer(session).data, status=status.HTTP_200_OK)


class ResumeAutonomousSessionView(APIView):
    def post(self, request, session_id: int, *args, **kwargs):
        session = resume_autonomous_session(session_id=session_id)
        return Response(AutonomousRuntimeSessionSerializer(session).data, status=status.HTTP_200_OK)


class StopAutonomousSessionView(APIView):
    def post(self, request, session_id: int, *args, **kwargs):
        session = stop_autonomous_session(session_id=session_id)
        return Response(AutonomousRuntimeSessionSerializer(session).data, status=status.HTTP_200_OK)


class RunAutonomousTickView(APIView):
    def post(self, request, session_id: int, *args, **kwargs):
        tick, cadence, recommendation = run_tick(session_id=session_id)
        return Response({
            'tick': AutonomousRuntimeTickSerializer(tick).data,
            'cadence_decision': AutonomousCadenceDecisionSerializer(cadence).data,
            'recommendation': AutonomousSessionRecommendationSerializer(recommendation).data,
        }, status=status.HTTP_200_OK)


class AutonomousSessionListView(generics.ListAPIView):
    serializer_class = AutonomousRuntimeSessionSerializer
    queryset = AutonomousRuntimeSession.objects.order_by('-started_at', '-id')[:100]


class AutonomousSessionDetailView(generics.RetrieveAPIView):
    serializer_class = AutonomousRuntimeSessionSerializer
    queryset = AutonomousRuntimeSession.objects.order_by('-started_at', '-id')


class AutonomousTickListView(generics.ListAPIView):
    serializer_class = AutonomousRuntimeTickSerializer
    queryset = AutonomousRuntimeTick.objects.select_related(
        'linked_session', 'linked_runtime_run', 'linked_cycle_plan', 'linked_cycle_execution', 'linked_cycle_outcome'
    ).order_by('-created_at', '-id')[:200]


class AutonomousTickDetailView(generics.RetrieveAPIView):
    serializer_class = AutonomousRuntimeTickSerializer
    queryset = AutonomousRuntimeTick.objects.select_related(
        'linked_session', 'linked_runtime_run', 'linked_cycle_plan', 'linked_cycle_execution', 'linked_cycle_outcome'
    ).order_by('-created_at', '-id')


class AutonomousCadenceDecisionListView(generics.ListAPIView):
    serializer_class = AutonomousCadenceDecisionSerializer
    queryset = AutonomousCadenceDecision.objects.select_related('linked_session', 'linked_previous_tick').order_by('-created_at', '-id')[:200]


class AutonomousSessionRecommendationListView(generics.ListAPIView):
    serializer_class = AutonomousSessionRecommendationSerializer
    queryset = AutonomousSessionRecommendation.objects.select_related(
        'target_session', 'target_tick', 'target_cadence_decision'
    ).order_by('-created_at', '-id')[:200]


class AutonomousSessionSummaryView(APIView):
    def get(self, request, *args, **kwargs):
        return Response(build_session_summary(), status=status.HTTP_200_OK)


class StartAutonomousRunnerView(APIView):
    def post(self, request, *args, **kwargs):
        runner = start_runner()
        return Response(AutonomousRunnerStateSerializer(runner).data, status=status.HTTP_200_OK)


class PauseAutonomousRunnerView(APIView):
    def post(self, request, *args, **kwargs):
        runner = pause_runner()
        return Response(AutonomousRunnerStateSerializer(runner).data, status=status.HTTP_200_OK)


class ResumeAutonomousRunnerView(APIView):
    def post(self, request, *args, **kwargs):
        runner = resume_runner()
        return Response(AutonomousRunnerStateSerializer(runner).data, status=status.HTTP_200_OK)


class StopAutonomousRunnerView(APIView):
    def post(self, request, *args, **kwargs):
        runner = stop_runner()
        return Response(AutonomousRunnerStateSerializer(runner).data, status=status.HTTP_200_OK)


class RunAutonomousHeartbeatView(APIView):
    def post(self, request, *args, **kwargs):
        heartbeat = run_heartbeat_pass()
        return Response(AutonomousHeartbeatRunSerializer(heartbeat).data, status=status.HTTP_200_OK)


class AutonomousRunnerStateView(APIView):
    def get(self, request, *args, **kwargs):
        return Response(AutonomousRunnerStateSerializer(get_runner_state()).data, status=status.HTTP_200_OK)


class AutonomousHeartbeatRunListView(generics.ListAPIView):
    serializer_class = AutonomousHeartbeatRunSerializer
    queryset = AutonomousHeartbeatRun.objects.order_by('-started_at', '-id')[:100]


class AutonomousHeartbeatDecisionListView(generics.ListAPIView):
    serializer_class = AutonomousHeartbeatDecisionSerializer
    queryset = AutonomousHeartbeatDecision.objects.select_related('linked_heartbeat_run', 'linked_session').order_by('-created_at', '-id')[:200]


class AutonomousTickDispatchAttemptListView(generics.ListAPIView):
    serializer_class = AutonomousTickDispatchAttemptSerializer
    queryset = AutonomousTickDispatchAttempt.objects.select_related('linked_session', 'linked_heartbeat_decision', 'linked_tick').order_by('-created_at', '-id')[:200]


class AutonomousHeartbeatRecommendationListView(generics.ListAPIView):
    serializer_class = AutonomousHeartbeatRecommendationSerializer
    queryset = AutonomousHeartbeatRecommendation.objects.select_related('target_session', 'target_heartbeat_decision').order_by('-created_at', '-id')[:200]


class AutonomousHeartbeatSummaryView(APIView):
    def get(self, request, *args, **kwargs):
        return Response(build_heartbeat_summary(), status=status.HTTP_200_OK)


class RunSessionTimingReviewView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = SessionTimingReviewRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        summary = run_session_timing_review(session_ids=payload.get('session_ids'))
        return Response(summary, status=status.HTTP_200_OK)


class ScheduleProfileListView(generics.ListAPIView):
    serializer_class = AutonomousScheduleProfileSerializer

    def get_queryset(self):
        ensure_default_schedule_profiles()
        return AutonomousScheduleProfile.objects.order_by('slug', '-id')


class SessionTimingSnapshotListView(generics.ListAPIView):
    serializer_class = AutonomousSessionTimingSnapshotSerializer
    queryset = AutonomousSessionTimingSnapshot.objects.select_related('linked_session', 'linked_schedule_profile').order_by('-created_at', '-id')[:300]


class StopConditionEvaluationListView(generics.ListAPIView):
    serializer_class = AutonomousStopConditionEvaluationSerializer
    queryset = AutonomousStopConditionEvaluation.objects.select_related('linked_session').order_by('-created_at', '-id')[:300]


class SessionTimingDecisionListView(generics.ListAPIView):
    serializer_class = AutonomousTimingDecisionSerializer
    queryset = AutonomousTimingDecision.objects.select_related('linked_session', 'linked_timing_snapshot').order_by('-created_at', '-id')[:300]


class SessionTimingRecommendationListView(generics.ListAPIView):
    serializer_class = AutonomousTimingRecommendationSerializer
    queryset = AutonomousTimingRecommendation.objects.select_related(
        'target_session', 'target_timing_snapshot', 'target_timing_decision'
    ).order_by('-created_at', '-id')[:300]


class SessionTimingSummaryView(APIView):
    def get(self, request, *args, **kwargs):
        return Response(build_session_timing_summary(), status=status.HTTP_200_OK)


class ApplyScheduleProfileView(APIView):
    def post(self, request, session_id: int, *args, **kwargs):
        profile_slug = (request.data or {}).get('profile_slug')
        if not profile_slug:
            return Response({'detail': 'profile_slug is required'}, status=status.HTTP_400_BAD_REQUEST)
        session = get_object_or_404(AutonomousRuntimeSession, pk=session_id)
        profile = AutonomousScheduleProfile.objects.filter(slug=profile_slug, is_active=True).first()
        if not profile:
            return Response({'detail': 'profile not found or inactive'}, status=status.HTTP_404_NOT_FOUND)
        apply_schedule_profile(session=session, profile=profile)
        return Response(AutonomousRuntimeSessionSerializer(session).data, status=status.HTTP_200_OK)


class RunProfileSelectionReviewView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = ProfileSelectionReviewRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        run = run_profile_selection_review(
            session_ids=payload.get('session_ids'),
            apply_switches=payload.get('apply_switches', True),
        )
        return Response(AutonomousProfileSelectionRunSerializer(run).data, status=status.HTTP_200_OK)


class SessionContextReviewListView(generics.ListAPIView):
    serializer_class = AutonomousSessionContextReviewSerializer
    queryset = AutonomousSessionContextReview.objects.select_related(
        'linked_selection_run', 'linked_session', 'linked_current_profile', 'linked_latest_timing_snapshot'
    ).order_by('-created_at', '-id')[:300]


class ProfileSwitchDecisionListView(generics.ListAPIView):
    serializer_class = AutonomousProfileSwitchDecisionSerializer
    queryset = AutonomousProfileSwitchDecision.objects.select_related(
        'linked_selection_run', 'linked_session', 'linked_context_review', 'from_profile', 'to_profile'
    ).order_by('-created_at', '-id')[:300]


class ProfileSwitchDecisionDetailView(generics.RetrieveAPIView):
    serializer_class = AutonomousProfileSwitchDecisionSerializer
    queryset = AutonomousProfileSwitchDecision.objects.select_related(
        'linked_selection_run', 'linked_session', 'linked_context_review', 'from_profile', 'to_profile'
    ).order_by('-created_at', '-id')


class ProfileSwitchRecordListView(generics.ListAPIView):
    serializer_class = AutonomousProfileSwitchRecordSerializer
    queryset = AutonomousProfileSwitchRecord.objects.select_related(
        'linked_selection_run', 'linked_session', 'linked_switch_decision', 'previous_profile', 'applied_profile'
    ).order_by('-created_at', '-id')[:300]


class ProfileRecommendationListView(generics.ListAPIView):
    serializer_class = AutonomousProfileRecommendationSerializer
    queryset = AutonomousProfileRecommendation.objects.select_related(
        'target_session', 'target_context_review', 'target_switch_decision'
    ).order_by('-created_at', '-id')[:300]


class ProfileSelectionSummaryView(APIView):
    def get(self, request, *args, **kwargs):
        return Response(build_profile_selection_summary(), status=status.HTTP_200_OK)


class ApplyProfileSwitchDecisionView(APIView):
    def post(self, request, decision_id: int, *args, **kwargs):
        decision = get_object_or_404(AutonomousProfileSwitchDecision, pk=decision_id)
        record = apply_profile_switch_decision(decision=decision, automatic=False)
        payload = {
            'decision': AutonomousProfileSwitchDecisionSerializer(decision).data,
            'record': AutonomousProfileSwitchRecordSerializer(record).data if record else None,
        }
        return Response(payload, status=status.HTTP_200_OK)
