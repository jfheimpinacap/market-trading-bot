from django.db.models import Count
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.risk_agent.models import PositionWatchEvent, RiskAssessment
from apps.memory_retrieval.models import MemoryQueryType
from apps.memory_retrieval.services import retrieve_precedents
from apps.risk_agent.serializers import (
    PositionWatchEventSerializer,
    RiskAssessRequestSerializer,
    RiskAssessmentSerializer,
    RiskSizeRequestSerializer,
    RiskSizingDecisionSerializer,
    RiskWatchRequestSerializer,
    PositionWatchRunSerializer,
)


class RiskAssessView(generics.GenericAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = RiskAssessRequestSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assessment = serializer.save()
        return Response({'assessment': RiskAssessmentSerializer(assessment).data}, status=status.HTTP_201_CREATED)


class RiskSizeView(generics.GenericAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = RiskSizeRequestSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        decision = serializer.save()
        return Response({'sizing': RiskSizingDecisionSerializer(decision).data}, status=status.HTTP_201_CREATED)


class RiskWatchRunView(generics.GenericAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = RiskWatchRequestSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        run = serializer.save()
        return Response({'watch_run': PositionWatchRunSerializer(run).data}, status=status.HTTP_201_CREATED)


class RiskAssessmentListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = RiskAssessmentSerializer

    def get_queryset(self):
        return RiskAssessment.objects.select_related('market', 'proposal', 'prediction_score').order_by('-created_at', '-id')[:40]


class RiskWatchEventListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PositionWatchEventSerializer

    def get_queryset(self):
        return PositionWatchEvent.objects.select_related('paper_position', 'paper_position__market', 'watch_run').order_by('-created_at', '-id')[:40]


class RiskSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        qs = RiskAssessment.objects.order_by('-created_at', '-id')
        by_level = list(qs.values('risk_level').annotate(count=Count('id')).order_by('risk_level'))
        latest = qs.first()
        return Response(
            {
                'total_assessments': qs.count(),
                'by_level': by_level,
                'latest_assessment': RiskAssessmentSerializer(latest).data if latest else None,
                'total_watch_events': PositionWatchEvent.objects.count(),
                'paper_demo_only': True,
                'real_execution_enabled': False,
            }
        )


class RiskPrecedentAssistView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        query_text = (request.data or {}).get('query_text')
        if not query_text:
            return Response({'detail': 'query_text is required.'}, status=status.HTTP_400_BAD_REQUEST)
        run = retrieve_precedents(
            query_text=query_text,
            query_type=MemoryQueryType.RISK,
            context_metadata={'assessment_id': (request.data or {}).get('assessment_id'), 'source': 'risk_agent'},
            limit=min(int((request.data or {}).get('limit', 6)), 12),
        )
        return Response({'retrieval_run_id': run.id, 'result_count': run.result_count}, status=status.HTTP_200_OK)
