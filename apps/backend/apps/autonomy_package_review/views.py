from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.autonomy_package.models import GovernancePackage
from apps.autonomy_package_review.models import PackageResolution, PackageReviewRecommendation, PackageReviewRun
from apps.autonomy_package_review.serializers import (
    PackageResolutionSerializer,
    PackageReviewActionSerializer,
    PackageReviewRecommendationSerializer,
)
from apps.autonomy_package_review.services import (
    acknowledge_package,
    adopt_package,
    build_package_review_candidates,
    defer_package,
    reject_package,
    run_package_resolution_review,
)


class AutonomyPackageReviewCandidatesView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response([candidate.__dict__ for candidate in build_package_review_candidates()], status=status.HTTP_200_OK)


class AutonomyPackageReviewRunView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = PackageReviewActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        result = run_package_resolution_review(actor=serializer.validated_data['actor'])
        return Response(
            {
                'run': result['run'].id,
                'candidate_count': len(result['candidates']),
                'recommendation_count': len(result['recommendations']),
            },
            status=status.HTTP_200_OK,
        )


class AutonomyPackageResolutionListView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = PackageResolution.objects.select_related('governance_package').order_by('-updated_at', '-id')[:500]
        return Response(PackageResolutionSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomyPackageResolutionDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, resolution_id: int, *args, **kwargs):
        try:
            row = PackageResolution.objects.get(pk=resolution_id)
        except PackageResolution.DoesNotExist:
            return Response({'detail': 'Package resolution not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(PackageResolutionSerializer(row).data, status=status.HTTP_200_OK)


class AutonomyPackageReviewRecommendationListView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = PackageReviewRecommendation.objects.select_related('governance_package').order_by('-created_at', '-id')[:500]
        return Response(PackageReviewRecommendationSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomyPackageReviewSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        latest = PackageReviewRun.objects.order_by('-created_at', '-id').first()
        return Response(
            {
                'latest_run_id': latest.id if latest else None,
                'candidate_count': latest.candidate_count if latest else 0,
                'pending_count': latest.pending_count if latest else 0,
                'acknowledged_count': latest.acknowledged_count if latest else 0,
                'adopted_count': latest.adopted_count if latest else 0,
                'deferred_count': latest.deferred_count if latest else 0,
                'rejected_count': latest.rejected_count if latest else 0,
                'blocked_count': latest.blocked_count if latest else 0,
                'closed_count': latest.closed_count if latest else 0,
                'recommendation_summary': latest.recommendation_summary if latest else {},
            },
            status=status.HTTP_200_OK,
        )


class _BasePackageActionView(APIView):
    authentication_classes = []
    permission_classes = []

    action = None

    def post(self, request, package_id: int, *args, **kwargs):
        serializer = PackageReviewActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        actor = serializer.validated_data['actor']
        rationale = serializer.validated_data.get('rationale', '')
        reason_codes = serializer.validated_data.get('reason_codes', [])

        try:
            package = GovernancePackage.objects.get(pk=package_id)
        except GovernancePackage.DoesNotExist:
            return Response({'detail': 'Governance package not found.'}, status=status.HTTP_404_NOT_FOUND)

        if not self.action:
            raise ValidationError('Package action not configured.')

        resolution = self.action(package=package, actor=actor, rationale=rationale, reason_codes=reason_codes)
        return Response({'package_id': package.id, 'resolution_status': resolution.resolution_status}, status=status.HTTP_200_OK)


class AutonomyPackageReviewAcknowledgeView(_BasePackageActionView):
    action = staticmethod(acknowledge_package)


class AutonomyPackageReviewAdoptView(_BasePackageActionView):
    action = staticmethod(adopt_package)


class AutonomyPackageReviewDeferView(_BasePackageActionView):
    action = staticmethod(defer_package)


class AutonomyPackageReviewRejectView(_BasePackageActionView):
    action = staticmethod(reject_package)
