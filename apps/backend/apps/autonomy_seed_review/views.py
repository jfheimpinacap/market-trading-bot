from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.autonomy_seed.models import GovernanceSeed
from apps.autonomy_seed_review.models import SeedResolution, SeedResolutionStatus, SeedReviewRecommendation, SeedReviewRun
from apps.autonomy_seed_review.serializers import SeedResolutionSerializer, SeedReviewActionSerializer, SeedReviewRecommendationSerializer
from apps.autonomy_seed_review.services import acknowledge_seed, build_seed_review_candidates, mark_seed_accepted, mark_seed_deferred, mark_seed_rejected, run_seed_resolution_review


class AutonomySeedReviewCandidatesView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response([candidate.__dict__ for candidate in build_seed_review_candidates()], status=status.HTTP_200_OK)


class AutonomySeedReviewRunView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = SeedReviewActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        result = run_seed_resolution_review(actor=serializer.validated_data['actor'])
        return Response(
            {
                'run': result['run'].id,
                'candidate_count': len(result['candidates']),
                'recommendation_count': len(result['recommendations']),
            },
            status=status.HTTP_200_OK,
        )


class AutonomySeedReviewResolutionsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = SeedResolution.objects.select_related('governance_seed').order_by('-updated_at', '-id')[:500]
        return Response(SeedResolutionSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomySeedReviewRecommendationsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = SeedReviewRecommendation.objects.select_related('governance_seed').order_by('-created_at', '-id')[:500]
        return Response(SeedReviewRecommendationSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomySeedReviewSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        latest = SeedReviewRun.objects.order_by('-created_at', '-id').first()
        resolution_counts = {
            'pending': SeedResolution.objects.filter(resolution_status=SeedResolutionStatus.PENDING).count(),
            'acknowledged': SeedResolution.objects.filter(resolution_status=SeedResolutionStatus.ACKNOWLEDGED).count(),
            'accepted': SeedResolution.objects.filter(resolution_status=SeedResolutionStatus.ACCEPTED).count(),
            'deferred': SeedResolution.objects.filter(resolution_status=SeedResolutionStatus.DEFERRED).count(),
            'rejected': SeedResolution.objects.filter(resolution_status=SeedResolutionStatus.REJECTED).count(),
            'blocked': SeedResolution.objects.filter(resolution_status=SeedResolutionStatus.BLOCKED).count(),
            'closed': SeedResolution.objects.filter(resolution_status=SeedResolutionStatus.CLOSED).count(),
        }
        return Response(
            {
                'latest_run_id': latest.id if latest else None,
                'seed_count': GovernanceSeed.objects.count(),
                'candidate_count': latest.candidate_count if latest else 0,
                'pending_count': latest.pending_count if latest else resolution_counts['pending'],
                'acknowledged_count': latest.acknowledged_count if latest else resolution_counts['acknowledged'],
                'accepted_count': latest.accepted_count if latest else resolution_counts['accepted'],
                'deferred_count': latest.deferred_count if latest else resolution_counts['deferred'],
                'rejected_count': latest.rejected_count if latest else resolution_counts['rejected'],
                'blocked_count': latest.blocked_count if latest else resolution_counts['blocked'],
                'closed_count': latest.closed_count if latest else resolution_counts['closed'],
                'recommendation_summary': latest.recommendation_summary if latest else {},
            },
            status=status.HTTP_200_OK,
        )


class _SeedResolutionActionView(APIView):
    authentication_classes = []
    permission_classes = []

    handler = None

    def post(self, request, seed_id: int, *args, **kwargs):
        serializer = SeedReviewActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        try:
            seed = GovernanceSeed.objects.get(pk=seed_id)
        except GovernanceSeed.DoesNotExist:
            return Response({'detail': 'Governance seed not found.'}, status=status.HTTP_404_NOT_FOUND)
        resolution = self.handler(seed=seed, actor=serializer.validated_data['actor'])
        return Response({'seed_id': seed.id, 'resolution_status': resolution.resolution_status}, status=status.HTTP_200_OK)


class AutonomySeedReviewAcknowledgeView(_SeedResolutionActionView):
    handler = staticmethod(acknowledge_seed)


class AutonomySeedReviewAcceptView(_SeedResolutionActionView):
    handler = staticmethod(mark_seed_accepted)


class AutonomySeedReviewDeferView(_SeedResolutionActionView):
    handler = staticmethod(mark_seed_deferred)


class AutonomySeedReviewRejectView(_SeedResolutionActionView):
    handler = staticmethod(mark_seed_rejected)
