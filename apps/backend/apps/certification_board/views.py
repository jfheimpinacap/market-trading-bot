from django.core.exceptions import ValidationError
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.certification_board.models import CertificationRun
from apps.certification_board.serializers import (
    ApplyCertificationDecisionRequestSerializer,
    CertificationRunSerializer,
    RunCertificationReviewRequestSerializer,
)
from apps.certification_board.services import (
    apply_certification_decision,
    build_certification_summary,
    get_current_certification,
    run_certification_review,
)


class CertificationRunReviewView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RunCertificationReviewRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        run = run_certification_review(
            decision_mode=serializer.validated_data.get('decision_mode', 'RECOMMENDATION_ONLY'),
            metadata=serializer.validated_data.get('metadata') or {},
        )
        return Response(CertificationRunSerializer(run).data, status=status.HTTP_201_CREATED)


class CertificationRunListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = CertificationRunSerializer

    def get_queryset(self):
        return CertificationRun.objects.select_related('evidence_snapshot', 'operating_envelope').prefetch_related('decision_logs').order_by('-created_at', '-id')[:50]


class CertificationRunDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = CertificationRunSerializer
    queryset = CertificationRun.objects.select_related('evidence_snapshot', 'operating_envelope').prefetch_related('decision_logs').order_by('-created_at', '-id')


class CurrentCertificationView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        run = get_current_certification()
        return Response({'current_certification': CertificationRunSerializer(run).data if run else None}, status=status.HTTP_200_OK)


class CertificationSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        summary = build_certification_summary()
        return Response(
            {
                'latest_run': CertificationRunSerializer(summary['latest_run']).data if summary['latest_run'] else None,
                'recent_runs': CertificationRunSerializer(summary['recent_runs'], many=True).data,
                'total_runs': summary['total_runs'],
                'level_counts': summary['level_counts'],
                'recommendation_counts': summary['recommendation_counts'],
            },
            status=status.HTTP_200_OK,
        )


class CertificationApplyView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, pk: int, *args, **kwargs):
        run = CertificationRun.objects.select_related('evidence_snapshot', 'operating_envelope').get(pk=pk)
        serializer = ApplyCertificationDecisionRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        try:
            run = apply_certification_decision(
                run=run,
                actor=serializer.validated_data['actor'],
                apply_safe_state=serializer.validated_data.get('apply_safe_state', False),
                notes=serializer.validated_data.get('notes', ''),
            )
        except ValidationError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(CertificationRunSerializer(run).data, status=status.HTTP_200_OK)
