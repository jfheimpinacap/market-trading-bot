from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.venue_account.models import (
    VenueAccountSnapshot,
    VenueBalanceSnapshot,
    VenueOrderSnapshot,
    VenuePositionSnapshot,
    VenueReconciliationRun,
)
from apps.venue_account.serializers import (
    VenueAccountSnapshotSerializer,
    VenueBalanceSnapshotSerializer,
    VenueOrderSnapshotSerializer,
    VenuePositionSnapshotSerializer,
    VenueReconciliationRequestSerializer,
    VenueReconciliationRunSerializer,
)
from apps.venue_account.services import build_summary, rebuild_sandbox_mirror, run_reconciliation


class VenueAccountCurrentView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rebuild_sandbox_mirror()
        current = VenueAccountSnapshot.objects.order_by('-created_at', '-id').first()
        if not current:
            return Response({}, status=status.HTTP_200_OK)
        return Response(VenueAccountSnapshotSerializer(current).data, status=status.HTTP_200_OK)


class VenueAccountOrdersView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = VenueOrderSnapshotSerializer

    def get_queryset(self):
        rebuild_sandbox_mirror()
        return VenueOrderSnapshot.objects.select_related('source_intent', 'source_paper_order').order_by('-updated_at', '-id')[:200]


class VenueAccountPositionsView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = VenuePositionSnapshotSerializer

    def get_queryset(self):
        rebuild_sandbox_mirror()
        return VenuePositionSnapshot.objects.select_related('source_internal_position').order_by('-updated_at', '-id')[:200]


class VenueAccountBalancesView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = VenueBalanceSnapshotSerializer

    def get_queryset(self):
        rebuild_sandbox_mirror()
        return VenueBalanceSnapshot.objects.select_related('account_snapshot').order_by('-created_at', '-id')[:50]


class VenueAccountRunReconciliationView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = VenueReconciliationRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        run = run_reconciliation(serializer.validated_data.get('metadata') or {})
        return Response(VenueReconciliationRunSerializer(run).data, status=status.HTTP_201_CREATED)


class VenueAccountReconciliationRunsView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = VenueReconciliationRunSerializer

    def get_queryset(self):
        return VenueReconciliationRun.objects.prefetch_related('issues').order_by('-created_at', '-id')[:100]


class VenueAccountReconciliationRunDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = VenueReconciliationRunSerializer
    queryset = VenueReconciliationRun.objects.prefetch_related('issues').all()


class VenueAccountSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rebuild_sandbox_mirror()
        return Response(build_summary(), status=status.HTTP_200_OK)
