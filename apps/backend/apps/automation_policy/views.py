from django.db.models import Count
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.automation_policy.models import AutomationActionLog, AutomationDecision
from apps.automation_policy.serializers import (
    AutomationActionLogSerializer,
    AutomationApplyProfileSerializer,
    AutomationDecisionSerializer,
    AutomationEvaluateRequestSerializer,
    AutomationPolicyProfileSerializer,
    AutomationPolicyRuleSerializer,
)
from apps.automation_policy.services import apply_profile, evaluate_action, execute_decision, get_active_profile, get_guardrail_snapshot, list_profiles, list_rules
from apps.runbook_engine.models import RunbookStep


class AutomationPolicyProfilesView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = AutomationPolicyProfileSerializer

    def get_queryset(self):
        return list_profiles()


class AutomationPolicyCurrentView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        profile = get_active_profile()
        rules = list_rules(profile=profile)
        guardrails = get_guardrail_snapshot()
        payload = {
            'profile': AutomationPolicyProfileSerializer(profile).data,
            'rules': AutomationPolicyRuleSerializer(rules, many=True).data,
            'guardrails': {
                'runtime_status': guardrails['runtime_state'].status if guardrails['runtime_state'] else None,
                'runtime_mode': guardrails['runtime_state'].current_mode if guardrails['runtime_state'] else None,
                'safety_status': guardrails['safety_config'].status if guardrails['safety_config'] else None,
                'certification_level': guardrails['certification_run'].certification_level if guardrails['certification_run'] else None,
                'degraded_mode_state': guardrails['degraded_mode'].state if guardrails['degraded_mode'] else None,
            },
        }
        return Response(payload, status=status.HTTP_200_OK)


class AutomationPolicyEvaluateView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = AutomationEvaluateRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        decision_result = evaluate_action(
            action_type=validated['action_type'],
            source_context_type=validated.get('source_context_type', ''),
            runbook_instance_id=validated.get('runbook_instance_id'),
            runbook_step_id=validated.get('runbook_step_id'),
            metadata=validated.get('metadata', {}),
        )

        action_log = None
        if validated.get('execute', False):
            step = None
            step_id = validated.get('runbook_step_id')
            if step_id:
                step = RunbookStep.objects.filter(pk=step_id).first()
            action_log = execute_decision(result=decision_result, runbook_step=step)

        payload = {
            'decision': AutomationDecisionSerializer(decision_result.decision).data,
            'flags': {
                'can_auto_execute': decision_result.can_auto_execute,
                'approval_required': decision_result.approval_required,
                'blocked': decision_result.blocked,
            },
            'action_log': AutomationActionLogSerializer(action_log).data if action_log else None,
        }
        return Response(payload, status=status.HTTP_200_OK)


class AutomationDecisionListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = AutomationDecisionSerializer

    def get_queryset(self):
        return AutomationDecision.objects.select_related('profile', 'rule').order_by('-created_at', '-id')[:100]


class AutomationActionLogListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = AutomationActionLogSerializer

    def get_queryset(self):
        return AutomationActionLog.objects.select_related('decision').order_by('-created_at', '-id')[:100]


class AutomationPolicyApplyProfileView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = AutomationApplyProfileSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        profile = apply_profile(profile_slug=serializer.validated_data['profile_slug'])
        return Response(AutomationPolicyProfileSerializer(profile).data, status=status.HTTP_200_OK)


class AutomationPolicySummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        profile = get_active_profile()
        decisions = AutomationDecision.objects.order_by('-created_at', '-id')[:50]
        action_logs = AutomationActionLog.objects.order_by('-created_at', '-id')[:50]

        decision_counts = {
            item['outcome']: item['count']
            for item in AutomationDecision.objects.values('outcome').annotate(count=Count('id'))
        }
        log_counts = {
            item['execution_status']: item['count']
            for item in AutomationActionLog.objects.values('execution_status').annotate(count=Count('id'))
        }

        data = {
            'active_profile': AutomationPolicyProfileSerializer(profile).data,
            'decision_counts': decision_counts,
            'log_counts': log_counts,
            'recent_decisions': AutomationDecisionSerializer(decisions, many=True).data,
            'recent_action_logs': AutomationActionLogSerializer(action_logs, many=True).data,
            'auto_eligible_action_types': [
                rule.action_type for rule in list_rules(profile=profile) if rule.trust_tier == 'SAFE_AUTOMATION'
            ],
            'blocked_action_types': [
                rule.action_type for rule in list_rules(profile=profile) if rule.trust_tier == 'AUTO_BLOCKED'
            ],
        }
        return Response(data, status=status.HTTP_200_OK)
