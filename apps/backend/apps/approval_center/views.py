from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.approval_center.models import ApprovalRequest
from apps.approval_center.serializers import ApprovalDecisionInputSerializer, ApprovalRequestSerializer
from apps.approval_center.services import apply_decision, get_approval_queue_summary, list_approvals


class ApprovalListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ApprovalRequestSerializer

    def get_queryset(self):
        status_filter = self.request.query_params.get('status')
        return list_approvals(status=status_filter)


class ApprovalPendingListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ApprovalRequestSerializer

    def get_queryset(self):
        return list_approvals(only_pending=True)


class ApprovalDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ApprovalRequestSerializer

    def get_queryset(self):
        return list_approvals()


class ApprovalSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(get_approval_queue_summary(), status=status.HTTP_200_OK)


class ApprovalDecisionBaseView(APIView):
    authentication_classes = []
    permission_classes = []
    decision_code = ''

    def post(self, request, pk, *args, **kwargs):
        approval = get_object_or_404(ApprovalRequest, pk=pk)
        serializer = ApprovalDecisionInputSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        updated = apply_decision(
            approval=approval,
            decision=self.decision_code,
            rationale=serializer.validated_data.get('rationale', ''),
            decided_by=serializer.validated_data.get('decided_by', 'local-operator'),
            metadata=serializer.validated_data.get('metadata') or {},
        )
        return Response(ApprovalRequestSerializer(updated).data, status=status.HTTP_200_OK)


class ApprovalApproveView(ApprovalDecisionBaseView):
    decision_code = 'APPROVE'


class ApprovalRejectView(ApprovalDecisionBaseView):
    decision_code = 'REJECT'


class ApprovalExpireView(ApprovalDecisionBaseView):
    decision_code = 'EXPIRE'


class ApprovalEscalateView(ApprovalDecisionBaseView):
    decision_code = 'ESCALATE'
