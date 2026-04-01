from django.db.models import Count
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.risk_agent.models import (
    AutonomousExecutionReadiness,
    PositionWatchEvent,
    PositionWatchPlan,
    RiskIntakeRecommendation,
    RiskApprovalDecision,
    RiskAssessment,
    RiskRuntimeCandidate,
    RiskRuntimeRun,
    RiskSizingPlan,
)
from apps.memory_retrieval.models import MemoryQueryType
from apps.memory_retrieval.services import run_assist
from apps.risk_agent.serializers import (
    AutonomousExecutionReadinessSerializer,
    PositionWatchEventSerializer,
    PositionWatchPlanSerializer,
    RiskAssessRequestSerializer,
    RiskApprovalDecisionSerializer,
    RiskAssessmentSerializer,
    RiskRuntimeCandidateSerializer,
    RiskIntakeRecommendationSerializer,
    RiskRuntimeReviewRequestSerializer,
    RiskRuntimeRunSerializer,
    RiskSizeRequestSerializer,
    RiskSizingPlanSerializer,
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
        run = run_assist(
            query_text=query_text,
            query_type=MemoryQueryType.RISK,
            context_metadata={'assessment_id': (request.data or {}).get('assessment_id'), 'source': 'risk_agent'},
            limit=min(int((request.data or {}).get('limit', 6)), 12),
        )
        return Response(
            {
                'retrieval_run_id': run.retrieval_run.id,
                'result_count': run.retrieval_run.result_count,
                'influence_mode': run.influence_mode,
                'precedent_confidence': run.precedent_confidence,
                'summary': run.summary,
            },
            status=status.HTTP_200_OK,
        )


class RiskRunRuntimeReviewView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RiskRuntimeReviewRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        run = serializer.save()
        return Response(RiskRuntimeRunSerializer(run).data, status=status.HTTP_201_CREATED)


class RiskRuntimeCandidateListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = RiskRuntimeCandidateSerializer

    def get_queryset(self):
        queryset = RiskRuntimeCandidate.objects.select_related('linked_market', 'linked_prediction_assessment', 'runtime_run')
        run_id = self.request.query_params.get('run_id')
        provider = self.request.query_params.get('provider')
        category = self.request.query_params.get('category')
        if run_id:
            queryset = queryset.filter(runtime_run_id=run_id)
        if provider:
            queryset = queryset.filter(market_provider=provider)
        if category:
            queryset = queryset.filter(category=category)
        return queryset.order_by('-created_at', '-id')[:200]


class RiskApprovalDecisionListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = RiskApprovalDecisionSerializer

    def get_queryset(self):
        queryset = RiskApprovalDecision.objects.select_related('linked_candidate__linked_market')
        status_code = self.request.query_params.get('status')
        run_id = self.request.query_params.get('run_id')
        if status_code:
            queryset = queryset.filter(approval_status=status_code)
        if run_id:
            queryset = queryset.filter(linked_candidate__runtime_run_id=run_id)
        return queryset.order_by('-created_at', '-id')[:200]


class RiskSizingPlanListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = RiskSizingPlanSerializer

    def get_queryset(self):
        queryset = RiskSizingPlan.objects.select_related('linked_candidate__linked_market', 'linked_approval_decision')
        run_id = self.request.query_params.get('run_id')
        if run_id:
            queryset = queryset.filter(linked_candidate__runtime_run_id=run_id)
        return queryset.order_by('-created_at', '-id')[:200]


class RiskWatchPlanListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PositionWatchPlanSerializer

    def get_queryset(self):
        queryset = PositionWatchPlan.objects.select_related('linked_candidate__linked_market', 'linked_sizing_plan')
        run_id = self.request.query_params.get('run_id')
        if run_id:
            queryset = queryset.filter(linked_candidate__runtime_run_id=run_id)
        return queryset.order_by('-created_at', '-id')[:200]


class RiskRuntimeRecommendationListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = RiskIntakeRecommendationSerializer

    def get_queryset(self):
        queryset = RiskIntakeRecommendation.objects.select_related('runtime_run', 'target_market')
        run_id = self.request.query_params.get('run_id')
        recommendation_type = self.request.query_params.get('recommendation_type')
        if run_id:
            queryset = queryset.filter(runtime_run_id=run_id)
        if recommendation_type:
            queryset = queryset.filter(recommendation_type=recommendation_type)
        return queryset.order_by('-created_at', '-id')[:200]


class AutonomousExecutionReadinessListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = AutonomousExecutionReadinessSerializer

    def get_queryset(self):
        queryset = AutonomousExecutionReadiness.objects.select_related('linked_market', 'linked_approval_review')
        run_id = self.request.query_params.get('run_id')
        if run_id:
            queryset = queryset.filter(linked_approval_review__linked_candidate__runtime_run_id=run_id)
        return queryset.order_by('-created_at', '-id')[:200]


class RiskRuntimeRunListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = RiskRuntimeRunSerializer

    def get_queryset(self):
        return RiskRuntimeRun.objects.order_by('-started_at', '-id')[:100]


class RiskRuntimeSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        latest_run = RiskRuntimeRun.objects.order_by('-started_at', '-id').first()
        if latest_run is None:
            return Response(
                {
                    'latest_run': None,
                    'approval_counts': {},
                    'recommendation_counts': {},
                    'paper_demo_only': True,
                    'real_execution_enabled': False,
                }
            )

        approval_counts = {
            row['approval_status']: row['count']
            for row in RiskApprovalDecision.objects.filter(linked_candidate__runtime_run=latest_run)
            .values('approval_status')
            .annotate(count=Count('id'))
        }
        recommendation_counts = {
            row['recommendation_type']: row['count']
            for row in RiskIntakeRecommendation.objects.filter(runtime_run=latest_run)
            .values('recommendation_type')
            .annotate(count=Count('id'))
        }
        return Response(
            {
                'latest_run': RiskRuntimeRunSerializer(latest_run).data,
                'approval_counts': approval_counts,
                'recommendation_counts': recommendation_counts,
                'paper_demo_only': True,
                'real_execution_enabled': False,
            }
        )
