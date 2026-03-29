from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.autonomy_decision.models import GovernanceDecision
from apps.autonomy_package.models import GovernancePackage, PackageRecommendation, PackageRun
from apps.autonomy_package.serializers import GovernancePackageSerializer, PackageActionSerializer, PackageRecommendationSerializer
from apps.autonomy_package.services import build_package_candidates, register_package_for_decision, run_package_review


class AutonomyPackageCandidatesView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response([candidate.__dict__ for candidate in build_package_candidates()], status=status.HTTP_200_OK)


class AutonomyPackageRunReviewView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = PackageActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        result = run_package_review(actor=serializer.validated_data['actor'])
        return Response(
            {
                'run': result['run'].id,
                'candidate_count': len(result['candidates']),
                'recommendation_count': len(result['recommendations']),
            },
            status=status.HTTP_200_OK,
        )


class AutonomyPackageListView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = GovernancePackage.objects.prefetch_related('linked_decisions').order_by('-updated_at', '-id')[:500]
        return Response(GovernancePackageSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomyPackageRecommendationListView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = PackageRecommendation.objects.select_related('governance_decision', 'governance_package').order_by('-created_at', '-id')[:500]
        return Response(PackageRecommendationSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomyPackageSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        latest = PackageRun.objects.order_by('-created_at', '-id').first()
        return Response(
            {
                'latest_run_id': latest.id if latest else None,
                'candidate_count': latest.candidate_count if latest else 0,
                'ready_count': latest.ready_count if latest else 0,
                'blocked_count': latest.blocked_count if latest else 0,
                'registered_count': latest.registered_count if latest else 0,
                'duplicate_skipped_count': latest.duplicate_skipped_count if latest else 0,
                'roadmap_package_count': latest.roadmap_package_count if latest else 0,
                'scenario_package_count': latest.scenario_package_count if latest else 0,
                'program_package_count': latest.program_package_count if latest else 0,
                'manager_package_count': latest.manager_package_count if latest else 0,
                'recommendation_summary': latest.recommendation_summary if latest else {},
            },
            status=status.HTTP_200_OK,
        )


class AutonomyPackageRegisterView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, decision_id: int, *args, **kwargs):
        serializer = PackageActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        try:
            package = register_package_for_decision(decision_id=decision_id, actor=serializer.validated_data['actor'])
        except ValidationError as err:
            return Response({'detail': str(err.message)}, status=status.HTTP_400_BAD_REQUEST)
        except GovernanceDecision.DoesNotExist:
            return Response({'detail': 'Governance decision does not exist for package registration.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'package_id': package.id, 'package_status': package.package_status}, status=status.HTTP_200_OK)


class AutonomyPackageAcknowledgeView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, package_id: int, *args, **kwargs):
        try:
            package = GovernancePackage.objects.get(pk=package_id)
        except GovernancePackage.DoesNotExist:
            return Response({'detail': 'Governance package not found.'}, status=status.HTTP_404_NOT_FOUND)
        package.package_status = 'ACKNOWLEDGED'
        package.metadata = {**(package.metadata or {}), 'acknowledged': True}
        package.save(update_fields=['package_status', 'metadata', 'updated_at'])
        return Response({'package_id': package.id, 'package_status': package.package_status}, status=status.HTTP_200_OK)
