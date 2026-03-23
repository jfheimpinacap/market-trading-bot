from django.db.models import Count, Q
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.policy_engine.models import ApprovalDecision, ApprovalDecisionType
from apps.policy_engine.serializers import (
    ApprovalDecisionSerializer,
    EvaluateTradePolicyRequestSerializer,
    PolicyDecisionSummarySerializer,
)


class EvaluateTradePolicyView(generics.GenericAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = EvaluateTradePolicyRequestSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        decision = serializer.save()
        return Response(ApprovalDecisionSerializer(decision).data, status=status.HTTP_201_CREATED)


class ApprovalDecisionListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ApprovalDecisionSerializer

    def get_queryset(self):
        queryset = ApprovalDecision.objects.select_related('market', 'paper_account', 'risk_assessment', 'linked_signal').order_by('-created_at', '-id')
        market = self.request.query_params.get('market')
        if market:
            queryset = queryset.filter(market_id=market)
        decision = self.request.query_params.get('decision')
        if decision:
            queryset = queryset.filter(decision=decision.upper())
        triggered_from = self.request.query_params.get('triggered_from')
        if triggered_from:
            queryset = queryset.filter(triggered_from=triggered_from)
        return queryset[:25]


class PolicyDecisionSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        base_queryset = ApprovalDecision.objects.all()
        counts = base_queryset.aggregate(
            total_decisions=Count('id'),
            auto_approve_count=Count('id', filter=Q(decision=ApprovalDecisionType.AUTO_APPROVE)),
            approval_required_count=Count('id', filter=Q(decision=ApprovalDecisionType.APPROVAL_REQUIRED)),
            hard_block_count=Count('id', filter=Q(decision=ApprovalDecisionType.HARD_BLOCK)),
        )
        payload = {
            **counts,
            'latest_decision': base_queryset.select_related('market', 'paper_account', 'risk_assessment', 'linked_signal').order_by('-created_at', '-id').first(),
        }
        serializer = PolicyDecisionSummarySerializer(payload)
        return Response(serializer.data)
