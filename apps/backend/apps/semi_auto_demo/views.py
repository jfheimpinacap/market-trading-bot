from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.semi_auto_demo.models import PendingApproval, PendingApprovalStatus, SemiAutoRun
from apps.semi_auto_demo.serializers import PendingApprovalDecisionSerializer, PendingApprovalSerializer, SemiAutoRunSerializer
from apps.semi_auto_demo.services import approve_pending_approval, reject_pending_approval, run_evaluate_only, run_scan_and_execute


class SemiAutoEvaluateView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        run = run_evaluate_only()
        return Response(SemiAutoRunSerializer(run).data, status=status.HTTP_200_OK)


class SemiAutoRunView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        run = run_scan_and_execute()
        return Response(SemiAutoRunSerializer(run).data, status=status.HTTP_200_OK)


class SemiAutoRunListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = SemiAutoRunSerializer

    def get_queryset(self):
        return SemiAutoRun.objects.order_by('-started_at', '-id')[:25]


class SemiAutoRunDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = SemiAutoRunSerializer
    queryset = SemiAutoRun.objects.order_by('-started_at', '-id')


class PendingApprovalListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PendingApprovalSerializer

    def get_queryset(self):
        queryset = PendingApproval.objects.select_related('proposal', 'market', 'paper_account', 'executed_trade').order_by('-created_at', '-id')
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter.upper())
        return queryset[:50]


class PendingApprovalApproveView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, pk, *args, **kwargs):
        serializer = PendingApprovalDecisionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        pending = get_object_or_404(PendingApproval, pk=pk)
        pending = approve_pending_approval(pending_approval=pending, decision_note=serializer.validated_data.get('decision_note', ''))
        return Response(PendingApprovalSerializer(pending).data, status=status.HTTP_200_OK)


class PendingApprovalRejectView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, pk, *args, **kwargs):
        serializer = PendingApprovalDecisionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        pending = get_object_or_404(PendingApproval, pk=pk)
        pending = reject_pending_approval(pending_approval=pending, decision_note=serializer.validated_data.get('decision_note', ''))
        return Response(PendingApprovalSerializer(pending).data, status=status.HTTP_200_OK)


class SemiAutoSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        latest_run = SemiAutoRun.objects.order_by('-started_at', '-id').first()
        payload = {
            'latest_run': SemiAutoRunSerializer(latest_run).data if latest_run else None,
            'pending_count': PendingApproval.objects.filter(status=PendingApprovalStatus.PENDING).count(),
            'executed_count': PendingApproval.objects.filter(status=PendingApprovalStatus.EXECUTED).count(),
            'rejected_count': PendingApproval.objects.filter(status=PendingApprovalStatus.REJECTED).count(),
            'safety': {
                'paper_only': True,
                'real_execution_enabled': False,
                'approval_required_behavior': 'create_pending_approval',
                'hard_block_behavior': 'never_execute',
            },
        }
        return Response(payload)
