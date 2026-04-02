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
)
from apps.runtime_governor.services import (
    apply_operating_mode_decision,
    get_capabilities_for_current_mode,
    get_operating_mode_summary,
    get_runtime_status,
    list_modes_with_constraints,
    run_operating_mode_review,
    set_runtime_mode,
)
from apps.runtime_governor.mode_enforcement.services import get_mode_enforcement_summary, run_mode_enforcement_review


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
