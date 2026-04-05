from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from django.shortcuts import get_object_or_404

from apps.runtime_governor.models import (
    GlobalOperatingModeDecision,
    GlobalOperatingModeRecommendation,
    GlobalOperatingModeSwitchRecord,
    GlobalRuntimePostureRun,
    GlobalRuntimePostureSnapshot,
    RuntimeTransitionLog,
    GlobalModeEnforcementRun,
    GlobalModeModuleImpact,
    GlobalModeEnforcementDecision,
    GlobalModeEnforcementRecommendation,
    RuntimeDiagnosticReview,
    RuntimeFeedbackDecision,
    RuntimeFeedbackApplyDecision,
    RuntimeFeedbackApplyRecommendation,
    RuntimeFeedbackApplyRecord,
    RuntimeFeedbackApplyRun,
    RuntimeModeStabilizationRecommendation,
    RuntimeModeStabilizationRun,
    RuntimeModeStabilityReview,
    RuntimeModeTransitionApplyRecord,
    RuntimeModeTransitionDecision,
    RuntimeModeTransitionSnapshot,
    RuntimeFeedbackRecommendation,
    RuntimeFeedbackRun,
    RuntimePerformanceSnapshot,
    RuntimeTuningContextSnapshot,
    RuntimeTuningReviewAction,
    RuntimeTuningReviewStatus,
)
from apps.runtime_governor.serializers import (
    GlobalOperatingModeDecisionSerializer,
    GlobalOperatingModeRecommendationSerializer,
    GlobalOperatingModeSwitchRecordSerializer,
    GlobalRuntimePostureRunSerializer,
    GlobalRuntimePostureSnapshotSerializer,
    RunOperatingModeReviewSerializer,
    RuntimeSetModeSerializer,
    RuntimeTransitionLogSerializer,
    RunModeEnforcementReviewSerializer,
    GlobalModeEnforcementRunSerializer,
    GlobalModeModuleImpactSerializer,
    GlobalModeEnforcementDecisionSerializer,
    GlobalModeEnforcementRecommendationSerializer,
    RunRuntimeFeedbackReviewSerializer,
    RuntimeDiagnosticReviewSerializer,
    RuntimeFeedbackDecisionSerializer,
    RuntimeFeedbackApplyDecisionSerializer,
    RuntimeFeedbackApplyRecommendationSerializer,
    RuntimeFeedbackApplyRecordSerializer,
    RuntimeFeedbackApplyRunSerializer,
    RuntimeModeStabilizationRecommendationSerializer,
    RuntimeModeStabilizationRunSerializer,
    RuntimeModeStabilityReviewSerializer,
    RuntimeModeTransitionApplyRecordSerializer,
    RuntimeModeTransitionDecisionSerializer,
    RuntimeModeTransitionSnapshotSerializer,
    RuntimeFeedbackRecommendationSerializer,
    RuntimeFeedbackRunSerializer,
    RuntimePerformanceSnapshotSerializer,
    RunRuntimeFeedbackApplyReviewSerializer,
    RunModeStabilizationReviewSerializer,
    RuntimeTuningProfileSummarySerializer,
    RuntimeTuningProfileValuesSerializer,
    RuntimeTuningContextSnapshotSerializer,
    RuntimeTuningContextDriftSummarySerializer,
    RuntimeTuningContextDiffSerializer,
    RuntimeTuningRunCorrelationSerializer,
    RuntimeTuningScopeDigestSerializer,
    RuntimeTuningChangeAlertSerializer,
    RuntimeTuningAlertSummarySerializer,
    RuntimeTuningReviewBoardRowSerializer,
    RuntimeTuningInvestigationPacketSerializer,
    RuntimeTuningScopeTimelineSerializer,
    RuntimeTuningCockpitPanelSerializer,
    RuntimeTuningCockpitPanelDetailSerializer,
    RuntimeTuningReviewQueueSerializer,
    RuntimeTuningReviewQueueDetailSerializer,
    RuntimeTuningReviewAgingSerializer,
    RuntimeTuningReviewAgingDetailSerializer,
    RuntimeTuningReviewEscalationSerializer,
    RuntimeTuningReviewEscalationDetailSerializer,
    RuntimeTuningReviewActionSerializer,
    RuntimeTuningReviewStateSerializer,
    RuntimeTuningReviewActivitySerializer,
    RuntimeTuningReviewActivityDetailSerializer,
)
from apps.runtime_governor.services import (
    apply_operating_mode_decision,
    get_capabilities_for_current_mode,
    get_operating_mode_summary,
    get_runtime_status,
    list_modes_with_constraints,
    run_operating_mode_review,
    set_runtime_mode,
    get_mode_stabilization_summary,
    run_mode_stabilization_review,
    apply_stabilized_transition_decision,
)
from apps.runtime_governor.services.tuning_summary import build_runtime_tuning_profile_snapshot
from apps.runtime_governor.services.tuning_history import build_tuning_context_drift_summary
from apps.runtime_governor.services.tuning_diff import build_tuning_context_diffs
from apps.runtime_governor.services.tuning_history_query import (
    parse_tuning_history_query,
    query_tuning_diff_snapshots,
    query_tuning_snapshots,
)
from apps.runtime_governor.services.tuning_correlation import build_tuning_run_correlations
from apps.runtime_governor.services.tuning_digest import build_tuning_scope_digest
from apps.runtime_governor.services.tuning_alerts import build_tuning_change_alerts
from apps.runtime_governor.services.tuning_alert_summary import build_tuning_alert_summary
from apps.runtime_governor.services.tuning_review_board import build_tuning_review_board, get_tuning_review_board_detail
from apps.runtime_governor.services.tuning_investigation import get_tuning_investigation_packet
from apps.runtime_governor.services.tuning_scope_timeline import build_tuning_scope_timeline
from apps.runtime_governor.services.tuning_cockpit_panel import build_tuning_cockpit_panel, get_tuning_cockpit_panel_detail
from apps.runtime_governor.services.tuning_review_queue import build_tuning_review_queue, get_tuning_review_queue_detail
from apps.runtime_governor.services.tuning_review_aging import build_tuning_review_aging, get_tuning_review_aging_detail
from apps.runtime_governor.services.tuning_review_escalation import (
    build_tuning_review_escalation,
    get_tuning_review_escalation_detail,
)
from apps.runtime_governor.services.tuning_review_state import (
    TuningScopeSnapshotNotFound,
    acknowledge_current_scope,
    clear_review_state,
    get_tuning_review_state_detail,
    list_tuning_review_actions,
    list_tuning_review_states,
    mark_followup_required,
)
from apps.runtime_governor.services.tuning_review_activity import (
    DEFAULT_ACTIVITY_LIMIT,
    build_tuning_review_activity,
    get_tuning_review_activity_detail,
)
from apps.runtime_governor.mode_enforcement.services import get_mode_enforcement_summary, run_mode_enforcement_review
from apps.runtime_governor.runtime_feedback.services import (
    get_runtime_feedback_summary,
    run_runtime_feedback_review,
)
from apps.runtime_governor.runtime_feedback_apply.services import (
    apply_feedback_decision_by_id,
    get_runtime_feedback_apply_summary,
    run_runtime_feedback_apply_review,
)


class RuntimeStatusView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        snapshot = get_runtime_status()
        payload = {
            'state': {
                'id': snapshot['state'].id,
                'current_mode': snapshot['state'].current_mode,
                'desired_mode': snapshot['state'].desired_mode,
                'status': snapshot['state'].status,
                'set_by': snapshot['state'].set_by,
                'rationale': snapshot['state'].rationale,
                'effective_at': snapshot['state'].effective_at,
                'updated_at': snapshot['state'].updated_at,
                'metadata': snapshot['state'].metadata,
            },
            'readiness_status': snapshot['readiness_status'],
            'safety_status': snapshot['safety_status'],
            'constraints': snapshot['constraints'],
            'global_operating_mode': snapshot['global_operating_mode'],
            'global_mode_influence': snapshot['global_mode_influence'],
        }
        return Response(payload, status=status.HTTP_200_OK)


class RuntimeModesView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(list_modes_with_constraints(), status=status.HTTP_200_OK)


class RuntimeSetModeView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RuntimeSetModeSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        result = set_runtime_mode(
            requested_mode=serializer.validated_data['mode'],
            set_by=serializer.validated_data.get('set_by', 'operator') or 'operator',
            rationale=serializer.validated_data.get('rationale', ''),
            metadata=serializer.validated_data.get('metadata', {}),
        )

        if not result['decision'].allowed:
            return Response(
                {
                    'changed': False,
                    'state': {
                        'current_mode': result['state'].current_mode,
                        'status': result['state'].status,
                    },
                    'blocked_reasons': result['decision'].reasons,
                    'message': 'This mode is currently blocked by readiness or safety constraints.',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                'changed': result['changed'],
                'state': {
                    'current_mode': result['state'].current_mode,
                    'status': result['state'].status,
                    'set_by': result['state'].set_by,
                    'rationale': result['state'].rationale,
                    'effective_at': result['state'].effective_at,
                },
                'reasons': result['decision'].reasons,
            },
            status=status.HTTP_200_OK,
        )


class RuntimeTransitionListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = RuntimeTransitionLogSerializer

    def get_queryset(self):
        return RuntimeTransitionLog.objects.order_by('-created_at', '-id')[:100]


class RuntimeCapabilitiesView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(get_capabilities_for_current_mode(), status=status.HTTP_200_OK)


class RuntimeTuningProfileSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        snapshot = build_runtime_tuning_profile_snapshot()
        serializer = RuntimeTuningProfileSummarySerializer(snapshot)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RuntimeTuningProfileValuesView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        snapshot = build_runtime_tuning_profile_snapshot()
        serializer = RuntimeTuningProfileValuesSerializer(snapshot)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RuntimeTuningContextSnapshotListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = RuntimeTuningContextSnapshotSerializer

    def get_queryset(self):
        query = parse_tuning_history_query(self.request.query_params, allow_drift_status=False)
        return query_tuning_snapshots(query)


class RuntimeTuningContextDriftSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        serializer = RuntimeTuningContextDriftSummarySerializer(build_tuning_context_drift_summary())
        return Response(serializer.data, status=status.HTTP_200_OK)


class RuntimeTuningContextDiffListView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        query = parse_tuning_history_query(request.query_params, allow_drift_status=True, allow_time_range=True)
        snapshots = query_tuning_diff_snapshots(query)
        serializer = RuntimeTuningContextDiffSerializer(build_tuning_context_diffs(snapshots=snapshots), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RuntimeTuningContextDiffDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, snapshot_id: int, *args, **kwargs):
        diffs = build_tuning_context_diffs(snapshot_id=snapshot_id)
        if not diffs:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = RuntimeTuningContextDiffSerializer(diffs[0])
        return Response(serializer.data, status=status.HTTP_200_OK)


class RuntimeTuningRunCorrelationListView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        query = parse_tuning_history_query(request.query_params, allow_drift_status=False)
        snapshots = query_tuning_snapshots(query)
        correlations = build_tuning_run_correlations(snapshots=snapshots)
        serializer = RuntimeTuningRunCorrelationSerializer(correlations, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RuntimeTuningScopeDigestListView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        source_scope = request.query_params.get('source_scope')
        serializer = RuntimeTuningScopeDigestSerializer(build_tuning_scope_digest(source_scope=source_scope), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RuntimeTuningChangeAlertListView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        source_scope = request.query_params.get('source_scope')
        serializer = RuntimeTuningChangeAlertSerializer(build_tuning_change_alerts(source_scope=source_scope), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RuntimeTuningChangeAlertSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        source_scope = request.query_params.get('source_scope')
        serializer = RuntimeTuningAlertSummarySerializer(build_tuning_alert_summary(source_scope=source_scope))
        return Response(serializer.data, status=status.HTTP_200_OK)


class RuntimeTuningReviewBoardListView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        source_scope = request.query_params.get('source_scope')
        attention_only = request.query_params.get('attention_only', 'false').lower() == 'true'
        limit_raw = request.query_params.get('limit')
        limit = None
        if limit_raw is not None:
            try:
                limit = int(limit_raw)
            except (TypeError, ValueError):
                limit = None
        serializer = RuntimeTuningReviewBoardRowSerializer(
            build_tuning_review_board(source_scope=source_scope, attention_only=attention_only, limit=limit),
            many=True,
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class RuntimeTuningReviewBoardDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, source_scope: str, *args, **kwargs):
        row = get_tuning_review_board_detail(source_scope=source_scope)
        if not row:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = RuntimeTuningReviewBoardRowSerializer(row)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RuntimeTuningReviewStateListView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        source_scope = request.query_params.get('source_scope')
        effective_status = request.query_params.get('effective_status')
        needs_attention_raw = request.query_params.get('needs_attention')
        needs_attention = None
        if needs_attention_raw is not None:
            needs_attention = needs_attention_raw.lower() == 'true'

        serializer = RuntimeTuningReviewStateSerializer(
            list_tuning_review_states(
                source_scope=source_scope,
                effective_status=effective_status,
                needs_attention=needs_attention,
            ),
            many=True,
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class RuntimeTuningReviewStateDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, source_scope: str, *args, **kwargs):
        try:
            payload = get_tuning_review_state_detail(source_scope=source_scope)
        except TuningScopeSnapshotNotFound:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = RuntimeTuningReviewStateSerializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RuntimeAcknowledgeTuningScopeView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, source_scope: str, *args, **kwargs):
        try:
            payload = acknowledge_current_scope(source_scope=source_scope)
        except TuningScopeSnapshotNotFound:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = RuntimeTuningReviewStateSerializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RuntimeMarkTuningScopeFollowupView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, source_scope: str, *args, **kwargs):
        try:
            payload = mark_followup_required(source_scope=source_scope)
        except TuningScopeSnapshotNotFound:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = RuntimeTuningReviewStateSerializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RuntimeClearTuningScopeReviewView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, source_scope: str, *args, **kwargs):
        try:
            payload = clear_review_state(source_scope=source_scope)
        except TuningScopeSnapshotNotFound:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = RuntimeTuningReviewStateSerializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RuntimeTuningReviewQueueListView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        unresolved_only = request.query_params.get('unresolved_only', 'true').lower() == 'true'
        effective_review_status = request.query_params.get('effective_review_status')
        limit_raw = request.query_params.get('limit')
        limit = 8
        if limit_raw is not None:
            try:
                limit = int(limit_raw)
            except (TypeError, ValueError):
                limit = 8

        serializer = RuntimeTuningReviewQueueSerializer(
            build_tuning_review_queue(
                unresolved_only=unresolved_only,
                effective_review_status=effective_review_status,
                limit=limit,
            )
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class RuntimeTuningReviewQueueDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, source_scope: str, *args, **kwargs):
        try:
            payload = get_tuning_review_queue_detail(source_scope=source_scope)
        except TuningScopeSnapshotNotFound:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = RuntimeTuningReviewQueueDetailSerializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RuntimeTuningReviewAgingListView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        unresolved_only = request.query_params.get('unresolved_only', 'true').lower() == 'true'
        age_bucket = request.query_params.get('age_bucket')
        limit_raw = request.query_params.get('limit')
        limit = 8
        if limit_raw is not None:
            try:
                limit = int(limit_raw)
            except (TypeError, ValueError):
                limit = 8

        serializer = RuntimeTuningReviewAgingSerializer(
            build_tuning_review_aging(
                unresolved_only=unresolved_only,
                age_bucket=age_bucket,
                limit=limit,
            )
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class RuntimeTuningReviewAgingDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, source_scope: str, *args, **kwargs):
        try:
            payload = get_tuning_review_aging_detail(source_scope=source_scope)
        except TuningScopeSnapshotNotFound:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = RuntimeTuningReviewAgingDetailSerializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RuntimeTuningReviewEscalationListView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        escalated_only = request.query_params.get('escalated_only', 'true').lower() == 'true'
        escalation_level = request.query_params.get('escalation_level')
        limit_raw = request.query_params.get('limit')
        limit = 6
        if limit_raw is not None:
            try:
                limit = int(limit_raw)
            except (TypeError, ValueError):
                limit = 6

        serializer = RuntimeTuningReviewEscalationSerializer(
            build_tuning_review_escalation(
                escalated_only=escalated_only,
                escalation_level=escalation_level,
                limit=limit,
            )
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class RuntimeTuningReviewEscalationDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, source_scope: str, *args, **kwargs):
        try:
            payload = get_tuning_review_escalation_detail(source_scope=source_scope)
        except TuningScopeSnapshotNotFound:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = RuntimeTuningReviewEscalationDetailSerializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RuntimeTuningReviewActionListView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        source_scope = request.query_params.get('source_scope')
        limit = None
        limit_raw = request.query_params.get('limit')
        if limit_raw is not None:
            try:
                limit = int(limit_raw)
            except (TypeError, ValueError):
                limit = None

        serializer = RuntimeTuningReviewActionSerializer(
            list_tuning_review_actions(source_scope=source_scope, limit=limit),
            many=True,
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class RuntimeTuningReviewActivityListView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        source_scope = request.query_params.get('source_scope')
        action_type = request.query_params.get('action_type')
        limit_raw = request.query_params.get('limit')
        limit = DEFAULT_ACTIVITY_LIMIT
        if limit_raw is not None:
            try:
                limit = int(limit_raw)
            except (TypeError, ValueError):
                limit = DEFAULT_ACTIVITY_LIMIT

        serializer = RuntimeTuningReviewActivitySerializer(
            build_tuning_review_activity(
                source_scope=source_scope,
                action_type=action_type,
                limit=limit,
            )
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class RuntimeTuningReviewActivityDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, source_scope: str, *args, **kwargs):
        try:
            payload = get_tuning_review_activity_detail(source_scope=source_scope)
        except TuningScopeSnapshotNotFound:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = RuntimeTuningReviewActivityDetailSerializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RuntimeTuningInvestigationDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, source_scope: str, *args, **kwargs):
        packet = get_tuning_investigation_packet(source_scope=source_scope)
        if not packet:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = RuntimeTuningInvestigationPacketSerializer(packet)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RuntimeTuningScopeTimelineDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, source_scope: str, *args, **kwargs):
        limit_raw = request.query_params.get('limit')
        include_stable = request.query_params.get('include_stable', 'true').lower() == 'true'
        limit = 5
        if limit_raw is not None:
            try:
                limit = int(limit_raw)
            except (TypeError, ValueError):
                limit = 5

        timeline = build_tuning_scope_timeline(source_scope=source_scope, limit=limit, include_stable=include_stable)
        if not timeline:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = RuntimeTuningScopeTimelineSerializer(timeline)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RuntimeTuningCockpitPanelListView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        source_scope = request.query_params.get('source_scope')
        attention_only = request.query_params.get('attention_only', 'true').lower() == 'true'
        limit_raw = request.query_params.get('limit')
        limit = 5
        if limit_raw is not None:
            try:
                limit = int(limit_raw)
            except (TypeError, ValueError):
                limit = 5

        serializer = RuntimeTuningCockpitPanelSerializer(
            build_tuning_cockpit_panel(source_scope=source_scope, attention_only=attention_only, limit=limit)
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class RuntimeTuningCockpitPanelDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, source_scope: str, *args, **kwargs):
        row = get_tuning_cockpit_panel_detail(source_scope=source_scope)
        if not row:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = RuntimeTuningCockpitPanelDetailSerializer(row)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RunOperatingModeReviewView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RunOperatingModeReviewSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        result = run_operating_mode_review(
            triggered_by=serializer.validated_data.get('triggered_by') or 'operator-ui',
            auto_apply=serializer.validated_data.get('auto_apply', True),
        )
        return Response(
            {
                'run_id': result['run'].id,
                'posture_snapshot_id': result['snapshot'].id,
                'mode_decision_id': result['decision'].id,
                'switch_record_id': result['switch_record'].id,
                'recommendation_id': result['recommendation'].id,
                'target_mode': result['decision'].target_mode,
                'decision_status': result['decision'].decision_status,
            },
            status=status.HTTP_200_OK,
        )


class RuntimePostureRunListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = GlobalRuntimePostureRunSerializer

    def get_queryset(self):
        return GlobalRuntimePostureRun.objects.order_by('-started_at', '-id')[:200]


class RuntimePostureSnapshotListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = GlobalRuntimePostureSnapshotSerializer

    def get_queryset(self):
        return GlobalRuntimePostureSnapshot.objects.order_by('-created_at_snapshot', '-id')[:300]


class OperatingModeDecisionListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = GlobalOperatingModeDecisionSerializer

    def get_queryset(self):
        return GlobalOperatingModeDecision.objects.select_related('linked_posture_snapshot').order_by('-created_at_decision', '-id')[:300]


class OperatingModeDecisionDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = GlobalOperatingModeDecisionSerializer
    queryset = GlobalOperatingModeDecision.objects.select_related('linked_posture_snapshot').all()
    lookup_field = 'id'
    lookup_url_kwarg = 'decision_id'


class OperatingModeSwitchRecordListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = GlobalOperatingModeSwitchRecordSerializer

    def get_queryset(self):
        return GlobalOperatingModeSwitchRecord.objects.select_related('linked_mode_decision').order_by('-created_at_switch', '-id')[:300]


class OperatingModeRecommendationListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = GlobalOperatingModeRecommendationSerializer

    def get_queryset(self):
        return GlobalOperatingModeRecommendation.objects.select_related('target_posture_snapshot', 'target_mode_decision').order_by('-created_at', '-id')[:300]


class OperatingModeSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(get_operating_mode_summary(), status=status.HTTP_200_OK)


class ApplyOperatingModeDecisionView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, decision_id: int, *args, **kwargs):
        decision = get_object_or_404(GlobalOperatingModeDecision, pk=decision_id)
        record = apply_operating_mode_decision(decision=decision)
        return Response(GlobalOperatingModeSwitchRecordSerializer(record).data, status=status.HTTP_200_OK)


class RunModeEnforcementReviewView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RunModeEnforcementReviewSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        result = run_mode_enforcement_review(triggered_by=serializer.validated_data.get('triggered_by') or 'operator-ui')
        return Response(
            {
                'run_id': result['run'].id,
                'impact_count': len(result['impacts']),
                'decision_count': len(result['decisions']),
                'recommendation_count': len(result['recommendations']),
            },
            status=status.HTTP_200_OK,
        )


class ModeEnforcementRunListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = GlobalModeEnforcementRunSerializer

    def get_queryset(self):
        return GlobalModeEnforcementRun.objects.order_by('-started_at', '-id')[:200]


class ModeModuleImpactListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = GlobalModeModuleImpactSerializer

    def get_queryset(self):
        return GlobalModeModuleImpact.objects.select_related('linked_enforcement_run').order_by('-created_at', '-id')[:400]


class ModeEnforcementDecisionListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = GlobalModeEnforcementDecisionSerializer

    def get_queryset(self):
        return GlobalModeEnforcementDecision.objects.select_related('linked_enforcement_run').order_by('-created_at', '-id')[:400]


class ModeEnforcementDecisionDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = GlobalModeEnforcementDecisionSerializer
    queryset = GlobalModeEnforcementDecision.objects.select_related('linked_enforcement_run').all()
    lookup_field = 'id'
    lookup_url_kwarg = 'enforcement_decision_id'


class ModeEnforcementRecommendationListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = GlobalModeEnforcementRecommendationSerializer

    def get_queryset(self):
        return GlobalModeEnforcementRecommendation.objects.select_related('target_enforcement_run').order_by('-created_at', '-id')[:400]


class ModeEnforcementSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(get_mode_enforcement_summary(), status=status.HTTP_200_OK)


class RunRuntimeFeedbackReviewView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RunRuntimeFeedbackReviewSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        result = run_runtime_feedback_review(
            triggered_by=serializer.validated_data.get('triggered_by') or 'operator-ui',
            auto_apply=serializer.validated_data.get('auto_apply', False),
        )
        return Response(
            {
                'run_id': result['run'].id,
                'performance_snapshot_id': result['snapshot'].id,
                'diagnostic_review_id': result['diagnostic'].id,
                'feedback_decision_id': result['decision'].id,
                'recommendation_id': result['recommendation'].id,
                'decision_type': result['decision'].decision_type,
                'decision_status': result['decision'].decision_status,
            },
            status=status.HTTP_200_OK,
        )


class RuntimeFeedbackRunListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = RuntimeFeedbackRunSerializer

    def get_queryset(self):
        return RuntimeFeedbackRun.objects.order_by('-started_at', '-id')[:200]


class RuntimePerformanceSnapshotListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = RuntimePerformanceSnapshotSerializer

    def get_queryset(self):
        return RuntimePerformanceSnapshot.objects.select_related('linked_feedback_run').order_by('-created_at', '-id')[:300]


class RuntimeDiagnosticReviewListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = RuntimeDiagnosticReviewSerializer

    def get_queryset(self):
        return RuntimeDiagnosticReview.objects.select_related('linked_performance_snapshot').order_by('-created_at', '-id')[:300]


class RuntimeFeedbackDecisionListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = RuntimeFeedbackDecisionSerializer

    def get_queryset(self):
        return RuntimeFeedbackDecision.objects.select_related('linked_performance_snapshot', 'linked_diagnostic_review').order_by('-created_at', '-id')[:300]


class RuntimeFeedbackDecisionDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = RuntimeFeedbackDecisionSerializer
    queryset = RuntimeFeedbackDecision.objects.select_related('linked_performance_snapshot', 'linked_diagnostic_review').all()
    lookup_field = 'id'
    lookup_url_kwarg = 'feedback_decision_id'


class RuntimeFeedbackRecommendationListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = RuntimeFeedbackRecommendationSerializer

    def get_queryset(self):
        return RuntimeFeedbackRecommendation.objects.select_related(
            'target_feedback_run',
            'target_diagnostic_review',
            'target_feedback_decision',
        ).order_by('-created_at', '-id')[:300]


class RuntimeFeedbackSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(get_runtime_feedback_summary(), status=status.HTTP_200_OK)


class ApplyRuntimeFeedbackDecisionView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, decision_id: int, *args, **kwargs):
        decision = get_object_or_404(RuntimeFeedbackDecision, pk=decision_id)
        result = apply_feedback_decision_by_id(feedback_decision=decision, triggered_by='runtime-page-manual')
        return Response(
            {
                'apply_decision': RuntimeFeedbackApplyDecisionSerializer(result['apply_decision']).data,
                'apply_record': RuntimeFeedbackApplyRecordSerializer(result['apply_record']).data,
            },
            status=status.HTTP_200_OK,
        )


class RunRuntimeFeedbackApplyReviewView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RunRuntimeFeedbackApplyReviewSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        result = run_runtime_feedback_apply_review(
            triggered_by=serializer.validated_data.get('triggered_by') or 'operator-ui',
            auto_apply=serializer.validated_data.get('auto_apply', False),
        )
        return Response(
            {
                'run_id': result['run'].id,
                'considered_feedback_decision_count': result['run'].considered_feedback_decision_count,
                'apply_decision_count': len(result['apply_decisions']),
                'apply_record_count': len(result['apply_records']),
                'recommendation_count': len(result['recommendations']),
            },
            status=status.HTTP_200_OK,
        )


class RuntimeFeedbackApplyRunListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = RuntimeFeedbackApplyRunSerializer

    def get_queryset(self):
        return RuntimeFeedbackApplyRun.objects.order_by('-started_at', '-id')[:200]


class RuntimeFeedbackApplyDecisionListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = RuntimeFeedbackApplyDecisionSerializer

    def get_queryset(self):
        return RuntimeFeedbackApplyDecision.objects.select_related('linked_feedback_decision').order_by('-created_at', '-id')[:300]


class RuntimeFeedbackApplyRecordListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = RuntimeFeedbackApplyRecordSerializer

    def get_queryset(self):
        return RuntimeFeedbackApplyRecord.objects.select_related('linked_apply_decision').order_by('-created_at', '-id')[:300]


class RuntimeFeedbackApplyRecommendationListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = RuntimeFeedbackApplyRecommendationSerializer

    def get_queryset(self):
        return RuntimeFeedbackApplyRecommendation.objects.select_related('target_feedback_decision', 'target_apply_decision').order_by('-created_at', '-id')[:300]


class RuntimeFeedbackApplySummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(get_runtime_feedback_apply_summary(), status=status.HTTP_200_OK)


class RunModeStabilizationReviewView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RunModeStabilizationReviewSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        result = run_mode_stabilization_review(
            triggered_by=serializer.validated_data.get('triggered_by') or 'operator-ui',
            auto_apply_safe=serializer.validated_data.get('auto_apply_safe', False),
        )
        return Response(
            {
                'run_id': result['run'].id,
                'considered_transition_count': result['run'].considered_transition_count,
                'snapshot_count': len(result['snapshots']),
                'review_count': len(result['reviews']),
                'decision_count': len(result['decisions']),
                'recommendation_count': len(result['recommendations']),
                'apply_record_count': len(result['apply_records']),
            },
            status=status.HTTP_200_OK,
        )


class ModeStabilizationRunListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = RuntimeModeStabilizationRunSerializer

    def get_queryset(self):
        return RuntimeModeStabilizationRun.objects.order_by('-started_at', '-id')[:200]


class ModeTransitionSnapshotListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = RuntimeModeTransitionSnapshotSerializer

    def get_queryset(self):
        return RuntimeModeTransitionSnapshot.objects.select_related('linked_feedback_decision', 'linked_run').order_by('-created_at', '-id')[:300]


class ModeStabilityReviewListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = RuntimeModeStabilityReviewSerializer

    def get_queryset(self):
        return RuntimeModeStabilityReview.objects.select_related('linked_transition_snapshot').order_by('-created_at', '-id')[:300]


class ModeTransitionDecisionListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = RuntimeModeTransitionDecisionSerializer

    def get_queryset(self):
        return RuntimeModeTransitionDecision.objects.select_related('linked_transition_snapshot', 'linked_stability_review').order_by('-created_at', '-id')[:300]


class ApplyStabilizedModeTransitionView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, decision_id: int, *args, **kwargs):
        transition_decision = get_object_or_404(RuntimeModeTransitionDecision, pk=decision_id)
        result = apply_stabilized_transition_decision(
            transition_decision=transition_decision,
            triggered_by='runtime-page-manual',
            auto_apply_safe=False,
        )
        return Response(RuntimeModeTransitionApplyRecordSerializer(result.apply_record).data, status=status.HTTP_200_OK)


class ModeTransitionApplyRecordListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = RuntimeModeTransitionApplyRecordSerializer

    def get_queryset(self):
        return RuntimeModeTransitionApplyRecord.objects.select_related('linked_transition_decision').order_by('-created_at', '-id')[:300]


class ModeStabilizationRecommendationListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = RuntimeModeStabilizationRecommendationSerializer

    def get_queryset(self):
        return RuntimeModeStabilizationRecommendation.objects.select_related(
            'target_transition_snapshot',
            'target_stability_review',
            'target_transition_decision',
        ).order_by('-created_at', '-id')[:300]


class ModeStabilizationSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(get_mode_stabilization_summary(), status=status.HTTP_200_OK)
