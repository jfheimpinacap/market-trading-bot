from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.portfolio_governor.models import (
    PortfolioExposureClusterSnapshot,
    PortfolioExposureConflictReview,
    PortfolioExposureCoordinationRun,
    PortfolioExposureDecision,
    PortfolioExposureRecommendation,
    PortfolioGovernanceRun,
    SessionExposureContribution,
)
from apps.portfolio_governor.serializers import (
    PortfolioExposureClusterSnapshotSerializer,
    PortfolioExposureConflictReviewSerializer,
    PortfolioExposureCoordinationRunSerializer,
    PortfolioExposureDecisionSerializer,
    PortfolioExposureRecommendationSerializer,
    PortfolioExposureSnapshotSerializer,
    PortfolioGovernanceRunSerializer,
    PortfolioThrottleDecisionSerializer,
    RunPortfolioGovernanceSerializer,
    SessionExposureContributionSerializer,
)
from apps.portfolio_governor.services import (
    build_exposure_coordination_summary,
    build_governance_summary,
    get_latest_exposure_snapshot,
    get_latest_throttle_decision,
    list_profiles,
    run_exposure_coordination_review,
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


class RunExposureCoordinationReviewView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        run = run_exposure_coordination_review()
        return Response(PortfolioExposureCoordinationRunSerializer(run).data, status=status.HTTP_200_OK)


class ExposureCoordinationRunListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PortfolioExposureCoordinationRunSerializer
    queryset = PortfolioExposureCoordinationRun.objects.order_by('-started_at', '-id')[:100]


class ExposureClusterSnapshotListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PortfolioExposureClusterSnapshotSerializer

    def get_queryset(self):
        return PortfolioExposureClusterSnapshot.objects.select_related('linked_run', 'linked_market').order_by('-created_at_snapshot', '-id')[:200]


class SessionExposureContributionListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = SessionExposureContributionSerializer

    def get_queryset(self):
        return SessionExposureContribution.objects.select_related('linked_session', 'linked_cluster_snapshot').order_by('-created_at_snapshot', '-id')[:400]


class ExposureConflictReviewListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PortfolioExposureConflictReviewSerializer

    def get_queryset(self):
        return PortfolioExposureConflictReview.objects.select_related('linked_cluster_snapshot').order_by('-created_at_review', '-id')[:300]


class ExposureDecisionListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PortfolioExposureDecisionSerializer

    def get_queryset(self):
        return PortfolioExposureDecision.objects.select_related('linked_cluster_snapshot', 'linked_conflict_review').order_by('-created_at_decision', '-id')[:300]


class ExposureRecommendationListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PortfolioExposureRecommendationSerializer

    def get_queryset(self):
        return PortfolioExposureRecommendation.objects.select_related(
            'target_cluster_snapshot',
            'target_conflict_review',
            'target_exposure_decision',
        ).order_by('-created_at', '-id')[:300]


class ExposureCoordinationSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(build_exposure_coordination_summary(), status=status.HTTP_200_OK)
