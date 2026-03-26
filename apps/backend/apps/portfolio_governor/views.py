from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.portfolio_governor.models import PortfolioGovernanceRun
from apps.portfolio_governor.serializers import (
    PortfolioExposureSnapshotSerializer,
    PortfolioGovernanceRunSerializer,
    PortfolioThrottleDecisionSerializer,
    RunPortfolioGovernanceSerializer,
)
from apps.portfolio_governor.services import (
    build_governance_summary,
    get_latest_exposure_snapshot,
    get_latest_throttle_decision,
    list_profiles,
    run_portfolio_governance,
)


class RunPortfolioGovernanceView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RunPortfolioGovernanceSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        run = run_portfolio_governance(profile_slug=serializer.validated_data.get('profile_slug'))
        return Response(PortfolioGovernanceRunSerializer(run).data, status=status.HTTP_200_OK)


class PortfolioGovernanceRunListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PortfolioGovernanceRunSerializer

    def get_queryset(self):
        return PortfolioGovernanceRun.objects.select_related('exposure_snapshot', 'throttle_decision').order_by('-started_at', '-id')[:100]


class PortfolioGovernanceRunDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PortfolioGovernanceRunSerializer
    queryset = PortfolioGovernanceRun.objects.select_related('exposure_snapshot', 'throttle_decision').order_by('-started_at', '-id')


class PortfolioExposureView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        snapshot = get_latest_exposure_snapshot()
        if snapshot is None:
            return Response({'detail': 'No exposure snapshot available yet.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(PortfolioExposureSnapshotSerializer(snapshot).data, status=status.HTTP_200_OK)


class PortfolioThrottleView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        decision = get_latest_throttle_decision()
        if decision is None:
            return Response({'detail': 'No throttle decision available yet.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(PortfolioThrottleDecisionSerializer(decision).data, status=status.HTTP_200_OK)


class PortfolioGovernanceSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        summary = build_governance_summary()
        summary['profiles'] = list_profiles()
        return Response(summary, status=status.HTTP_200_OK)
