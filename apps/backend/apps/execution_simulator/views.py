from django.db.models import Count
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.execution_simulator.models import PaperExecutionAttempt, PaperFill, PaperOrder
from apps.execution_simulator.serializers import (
    CreateOrderRequestSerializer,
    PaperFillSerializer,
    PaperOrderSerializer,
    PaperOrderLifecycleRunSerializer,
    RunLifecycleRequestSerializer,
)


class ExecutionCreateOrderView(generics.GenericAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = CreateOrderRequestSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        return Response({'order': PaperOrderSerializer(order).data}, status=status.HTTP_201_CREATED)


class ExecutionRunLifecycleView(generics.GenericAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = RunLifecycleRequestSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        run = serializer.save()
        return Response({'lifecycle_run': PaperOrderLifecycleRunSerializer(run).data}, status=status.HTTP_201_CREATED)


class ExecutionOrdersView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PaperOrderSerializer

    def get_queryset(self):
        return PaperOrder.objects.select_related('market', 'paper_account').order_by('-created_at', '-id')[:200]


class ExecutionOrderDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PaperOrderSerializer
    queryset = PaperOrder.objects.select_related('market', 'paper_account').prefetch_related('fills', 'attempts').order_by('-created_at', '-id')


class ExecutionFillsView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PaperFillSerializer

    def get_queryset(self):
        return PaperFill.objects.select_related('paper_order', 'paper_order__market').order_by('-created_at', '-id')[:300]


class ExecutionSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        status_counts = list(PaperOrder.objects.values('status').annotate(count=Count('id')).order_by('status'))
        attempt_counts = list(PaperExecutionAttempt.objects.values('attempt_status').annotate(count=Count('id')).order_by('attempt_status'))
        return Response(
            {
                'total_orders': PaperOrder.objects.count(),
                'total_fills': PaperFill.objects.count(),
                'status_counts': status_counts,
                'attempt_status_counts': attempt_counts,
                'paper_demo_only': True,
                'real_execution_enabled': False,
            },
            status=status.HTTP_200_OK,
        )
