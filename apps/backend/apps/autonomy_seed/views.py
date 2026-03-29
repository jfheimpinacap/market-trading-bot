from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.autonomy_package.models import GovernancePackage
from apps.autonomy_seed.models import GovernanceSeed, GovernanceSeedStatus, SeedRecommendation, SeedRun
from apps.autonomy_seed.serializers import GovernanceSeedSerializer, SeedActionSerializer, SeedRecommendationSerializer
from apps.autonomy_seed.services import build_seed_candidates, register_seed_for_package, run_seed_review


class AutonomySeedCandidatesView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response([candidate.__dict__ for candidate in build_seed_candidates()], status=status.HTTP_200_OK)


class AutonomySeedRunReviewView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = SeedActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        result = run_seed_review(actor=serializer.validated_data['actor'])
        return Response(
            {
                'run': result['run'].id,
                'candidate_count': len(result['candidates']),
                'recommendation_count': len(result['recommendations']),
            },
            status=status.HTTP_200_OK,
        )


class AutonomySeedListView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = GovernanceSeed.objects.select_related('governance_package', 'package_resolution').order_by('-updated_at', '-id')[:500]
        return Response(GovernanceSeedSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomySeedRecommendationsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = SeedRecommendation.objects.select_related('governance_package', 'governance_seed').order_by('-created_at', '-id')[:500]
        return Response(SeedRecommendationSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomySeedSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        latest = SeedRun.objects.order_by('-created_at', '-id').first()
        return Response(
            {
                'latest_run_id': latest.id if latest else None,
                'candidate_count': latest.candidate_count if latest else 0,
                'ready_count': latest.ready_count if latest else 0,
                'blocked_count': latest.blocked_count if latest else 0,
                'registered_count': latest.registered_count if latest else 0,
                'duplicate_skipped_count': latest.duplicate_skipped_count if latest else 0,
                'roadmap_seed_count': latest.roadmap_seed_count if latest else 0,
                'scenario_seed_count': latest.scenario_seed_count if latest else 0,
                'program_seed_count': latest.program_seed_count if latest else 0,
                'manager_seed_count': latest.manager_seed_count if latest else 0,
                'recommendation_summary': latest.recommendation_summary if latest else {},
            },
            status=status.HTTP_200_OK,
        )


class AutonomySeedRegisterView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, package_id: int, *args, **kwargs):
        serializer = SeedActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        try:
            seed = register_seed_for_package(package_id=package_id, actor=serializer.validated_data['actor'])
        except ValidationError as err:
            return Response({'detail': str(err.message)}, status=status.HTTP_400_BAD_REQUEST)
        except GovernancePackage.DoesNotExist:
            return Response({'detail': 'Governance package does not exist for seed registration.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'seed_id': seed.id, 'seed_status': seed.seed_status}, status=status.HTTP_200_OK)


class AutonomySeedAcknowledgeView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, seed_id: int, *args, **kwargs):
        try:
            seed = GovernanceSeed.objects.get(pk=seed_id)
        except GovernanceSeed.DoesNotExist:
            return Response({'detail': 'Governance seed not found.'}, status=status.HTTP_404_NOT_FOUND)
        seed.seed_status = GovernanceSeedStatus.ACKNOWLEDGED
        seed.metadata = {**(seed.metadata or {}), 'acknowledged': True}
        seed.save(update_fields=['seed_status', 'metadata', 'updated_at'])
        return Response({'seed_id': seed.id, 'seed_status': seed.seed_status}, status=status.HTTP_200_OK)
