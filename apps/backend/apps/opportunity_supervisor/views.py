from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.opportunity_supervisor.models import OpportunityCycleItem, OpportunityCycleRun
from apps.opportunity_supervisor.models import OpportunityCycleRuntimeRun, OpportunityFusionAssessment, OpportunityFusionCandidate, OpportunityRecommendation, PaperOpportunityProposal
from apps.opportunity_supervisor.serializers import (
    OpportunityCycleItemSerializer,
    OpportunityCycleRunSerializer,
    OpportunityCycleRuntimeRunSerializer,
    OpportunityFusionAssessmentSerializer,
    OpportunityFusionCandidateSerializer,
    OpportunityRecommendationSerializer,
    PaperOpportunityProposalSerializer,
    RunOpportunityCycleSerializer,
)
from apps.opportunity_supervisor.services import build_summary, list_profiles, run_opportunity_cycle, run_opportunity_cycle_review


class OpportunityRunCycleView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RunOpportunityCycleSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        cycle = run_opportunity_cycle(profile_slug=serializer.validated_data.get('profile_slug'))
        return Response(OpportunityCycleRunSerializer(cycle).data, status=status.HTTP_200_OK)


class OpportunityCycleListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = OpportunityCycleRunSerializer

    def get_queryset(self):
        return OpportunityCycleRun.objects.order_by('-started_at', '-id')[:100]


class OpportunityCycleDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = OpportunityCycleRunSerializer
    queryset = OpportunityCycleRun.objects.order_by('-started_at', '-id')


class OpportunityItemListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = OpportunityCycleItemSerializer

    def get_queryset(self):
        queryset = OpportunityCycleItem.objects.select_related('market', 'proposal', 'execution_plan').order_by('-created_at', '-id')
        run_id = self.request.query_params.get('run_id')
        if run_id and run_id.isdigit():
            queryset = queryset.filter(run_id=int(run_id))
        return queryset[:500]


class OpportunitySummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        payload = build_summary()
        payload['profiles'] = list_profiles()
        return Response(payload, status=status.HTTP_200_OK)


class OpportunityCycleRunReviewView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        run = run_opportunity_cycle_review(triggered_by='manual_api')
        return Response(OpportunityCycleRuntimeRunSerializer(run).data, status=status.HTTP_200_OK)


class OpportunityCycleCandidateListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = OpportunityFusionCandidateSerializer

    def get_queryset(self):
        queryset = OpportunityFusionCandidate.objects.select_related('linked_market').order_by('-created_at', '-id')
        run_id = self.request.query_params.get('run_id')
        provider = self.request.query_params.get('provider')
        category = self.request.query_params.get('category')
        if run_id and run_id.isdigit():
            queryset = queryset.filter(runtime_run_id=int(run_id))
        if provider:
            queryset = queryset.filter(provider=provider)
        if category:
            queryset = queryset.filter(category=category)
        return queryset[:500]


class OpportunityCycleAssessmentListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = OpportunityFusionAssessmentSerializer

    def get_queryset(self):
        queryset = OpportunityFusionAssessment.objects.select_related('linked_candidate', 'linked_candidate__linked_market').order_by('-created_at', '-id')
        run_id = self.request.query_params.get('run_id')
        status_filter = self.request.query_params.get('status')
        if run_id and run_id.isdigit():
            queryset = queryset.filter(runtime_run_id=int(run_id))
        if status_filter:
            queryset = queryset.filter(fusion_status=status_filter)
        return queryset[:500]


class OpportunityCycleProposalListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PaperOpportunityProposalSerializer

    def get_queryset(self):
        queryset = PaperOpportunityProposal.objects.select_related(
            'linked_assessment',
            'linked_assessment__linked_candidate',
            'linked_assessment__linked_candidate__linked_market',
        ).order_by('-created_at', '-id')
        run_id = self.request.query_params.get('run_id')
        status_filter = self.request.query_params.get('status')
        if run_id and run_id.isdigit():
            queryset = queryset.filter(runtime_run_id=int(run_id))
        if status_filter:
            queryset = queryset.filter(proposal_status=status_filter)
        return queryset[:500]


class OpportunityCycleRecommendationListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = OpportunityRecommendationSerializer

    def get_queryset(self):
        queryset = OpportunityRecommendation.objects.select_related(
            'target_assessment',
            'target_assessment__linked_candidate',
            'target_assessment__linked_candidate__linked_market',
        ).order_by('-created_at', '-id')
        run_id = self.request.query_params.get('run_id')
        recommendation = self.request.query_params.get('recommendation')
        if run_id and run_id.isdigit():
            queryset = queryset.filter(runtime_run_id=int(run_id))
        if recommendation:
            queryset = queryset.filter(recommendation_type=recommendation)
        return queryset[:500]


class OpportunityCycleSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        latest = OpportunityCycleRuntimeRun.objects.order_by('-started_at', '-id').first()
        payload = OpportunityCycleRuntimeRunSerializer(latest).data if latest else {
            'candidate_count': 0,
            'fused_count': 0,
            'ready_for_proposal_count': 0,
            'watch_count': 0,
            'blocked_count': 0,
            'sent_to_proposal_count': 0,
            'sent_to_execution_sim_context_count': 0,
            'recommendation_summary': {},
            'metadata': {'paper_only': True, 'manual_first': True},
        }
        return Response(payload, status=status.HTTP_200_OK)
