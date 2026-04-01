from django.db.models import Count
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.research_agent.models import (
    NarrativeConsensusRecommendation,
    NarrativeConsensusRun,
    NarrativeConsensusRecord,
    NarrativeMarketDivergenceRecord,
    ResearchHandoffPriority,
    ResearchPursuitRecommendation,
    ResearchPursuitRun,
    ResearchPursuitScore,
    ResearchStructuralAssessment,
    PredictionHandoffCandidate,
    MarketUniverseRun,
    MarketUniverseScanRun,
    MarketResearchCandidate,
    MarketTriageDecisionV2,
    MarketResearchRecommendation,
    NarrativeCluster,
    NarrativeItem,
    NarrativeSignal,
    NarrativeSource,
    NarrativeSourceType,
    PursuitCandidate,
    ResearchCandidate,
    ResearchScanRun,
    ScanRecommendation,
    SourceScanRun,
)
from apps.research_agent.serializers import (
    NarrativeConsensusRecommendationSerializer,
    NarrativeConsensusRunSerializer,
    NarrativeConsensusRecordSerializer,
    NarrativeMarketDivergenceRecordSerializer,
    ResearchHandoffPrioritySerializer,
    ResearchPursuitRecommendationSerializer,
    ResearchPursuitRunSerializer,
    ResearchPursuitScoreSerializer,
    ResearchStructuralAssessmentSerializer,
    PredictionHandoffCandidateSerializer,
    MarketUniverseRunSerializer,
    MarketUniverseScanRunSerializer,
    MarketResearchCandidateSerializer,
    MarketTriageDecisionV2Serializer,
    MarketResearchRecommendationSerializer,
    ResearchUniverseRunRequestSerializer,
    NarrativeClusterSerializer,
    NarrativeItemSerializer,
    NarrativeSignalSerializer,
    NarrativeSourceCreateSerializer,
    NarrativeSourceSerializer,
    PursuitCandidateSerializer,
    ResearchCandidateSerializer,
    ResearchRunRequestSerializer,
    RunPursuitReviewRequestSerializer,
    ResearchScanRunSerializer,
    ScanRecommendationSerializer,
    ScanRunRequestSerializer,
    SourceScanRunSerializer,
    TriageToPredictionRequestSerializer,
    UniverseScanRunRequestSerializer,
)
from apps.research_agent.services.run import get_latest_universe_summary, run_market_universe_triage, run_scan_agent
from apps.research_agent.services.pursuit_scoring.run import get_latest_pursuit_summary, run_pursuit_review
from apps.research_agent.services.intelligence_handoff.run import get_consensus_summary, run_consensus_review
from apps.research_agent.services.analyze import run_narrative_analysis
from apps.research_agent.services.pursuit_board import get_latest_board_summary, get_pursuit_candidates_queryset
from apps.research_agent.services.scan import run_full_research_scan, run_research_scan
from apps.research_agent.services.universe_scan import run_triage_to_prediction, run_universe_scan
from apps.memory_retrieval.models import MemoryQueryType
from apps.memory_retrieval.services import run_assist


class ResearchSourceListCreateView(generics.ListCreateAPIView):
    authentication_classes = []
    permission_classes = []

    def get_queryset(self):
        return NarrativeSource.objects.order_by('name')

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return NarrativeSourceCreateSerializer
        return NarrativeSourceSerializer


class ResearchRunIngestView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = ResearchRunRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        run = run_research_scan(
            source_ids=serializer.validated_data.get('source_ids'),
            run_analysis=serializer.validated_data.get('run_analysis', True),
        )
        return Response(ResearchScanRunSerializer(run).data, status=status.HTTP_200_OK)


class ResearchRunFullScanView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = ResearchRunRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        run = run_full_research_scan(source_ids=serializer.validated_data.get('source_ids'))
        return Response(ResearchScanRunSerializer(run).data, status=status.HTTP_200_OK)


class ResearchRunAnalysisView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        result = run_narrative_analysis()
        return Response({'analyzed': result.analyzed, 'errors': result.errors}, status=status.HTTP_200_OK)


class ResearchRunUniverseScanView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = UniverseScanRunRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        run = run_universe_scan(
            filter_profile=serializer.validated_data.get('filter_profile'),
            provider_scope=serializer.validated_data.get('provider_scope'),
            source_scope=serializer.validated_data.get('source_scope'),
            triggered_by='manual_api',
        )
        return Response(MarketUniverseScanRunSerializer(run).data, status=status.HTTP_200_OK)


class UniverseScanRunListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = MarketUniverseScanRunSerializer

    def get_queryset(self):
        return MarketUniverseScanRun.objects.order_by('-started_at', '-id')[:50]


class UniverseScanRunDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = MarketUniverseScanRunSerializer

    def get_queryset(self):
        return MarketUniverseScanRun.objects.order_by('-started_at', '-id')


class NarrativeItemListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = NarrativeItemSerializer

    def get_queryset(self):
        return NarrativeItem.objects.select_related('source', 'analysis').annotate(linked_market_count=Count('market_links')).order_by('-ingested_at', '-id')[:200]


class NarrativeItemDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = NarrativeItemSerializer

    def get_queryset(self):
        return NarrativeItem.objects.select_related('source', 'analysis').annotate(linked_market_count=Count('market_links')).order_by('-ingested_at', '-id')


class ResearchCandidateListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ResearchCandidateSerializer

    def get_queryset(self):
        return ResearchCandidate.objects.select_related('market').annotate(linked_item_count=Count('narrative_items')).order_by('-priority', '-updated_at')[:100]


class PursuitCandidateListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PursuitCandidateSerializer

    def get_queryset(self):
        status_filter = self.request.query_params.get('status')
        run_id = self.request.query_params.get('run_id')
        queryset = get_pursuit_candidates_queryset(status=status_filter)
        if run_id:
            queryset = queryset.filter(run_id=run_id)
        return queryset


class ResearchBoardSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(get_latest_board_summary(), status=status.HTTP_200_OK)


class ResearchTriageToPredictionView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = TriageToPredictionRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        run = MarketUniverseScanRun.objects.filter(id=serializer.validated_data['run_id']).first()
        if not run:
            return Response({'detail': 'Universe scan run not found.'}, status=status.HTTP_404_NOT_FOUND)
        payload = run_triage_to_prediction(run=run, limit=serializer.validated_data['limit'])
        return Response(payload, status=status.HTTP_200_OK)


class ResearchSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        latest_run = ResearchScanRun.objects.order_by('-started_at', '-id').first()
        latest_universe_run = MarketUniverseScanRun.objects.order_by('-started_at', '-id').first()
        payload = {
            'source_count': NarrativeSource.objects.filter(is_enabled=True).count(),
            'rss_source_count': NarrativeSource.objects.filter(is_enabled=True, source_type=NarrativeSourceType.RSS).count(),
            'reddit_source_count': NarrativeSource.objects.filter(is_enabled=True, source_type=NarrativeSourceType.REDDIT).count(),
            'twitter_source_count': NarrativeSource.objects.filter(is_enabled=True, source_type=NarrativeSourceType.TWITTER).count(),
            'item_count': NarrativeItem.objects.count(),
            'rss_item_count': NarrativeItem.objects.filter(source__source_type=NarrativeSourceType.RSS).count(),
            'reddit_item_count': NarrativeItem.objects.filter(source__source_type=NarrativeSourceType.REDDIT).count(),
            'twitter_item_count': NarrativeItem.objects.filter(source__source_type=NarrativeSourceType.TWITTER).count(),
            'social_item_count': NarrativeItem.objects.filter(
                source__source_type__in=[NarrativeSourceType.REDDIT, NarrativeSourceType.TWITTER]
            ).count(),
            'analyzed_count': NarrativeItem.objects.filter(analysis__isnull=False).count(),
            'candidate_count': ResearchCandidate.objects.count(),
            'mixed_candidate_count': ResearchCandidate.objects.filter(
                source_mix__in=['mixed', 'social_heavy', 'news_confirmed', 'full_signal']
            ).count(),
            'latest_run': ResearchScanRunSerializer(latest_run).data if latest_run else None,
            'latest_universe_scan': MarketUniverseScanRunSerializer(latest_universe_run).data if latest_universe_run else None,
            'pursuit_candidate_count': PursuitCandidate.objects.count(),
        }
        return Response(payload, status=status.HTTP_200_OK)


class ResearchPrecedentAssistView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        query_text = (request.data or {}).get('query_text')
        if not query_text:
            return Response({'detail': 'query_text is required.'}, status=status.HTTP_400_BAD_REQUEST)
        run = run_assist(
            query_text=query_text,
            query_type=MemoryQueryType.RESEARCH,
            context_metadata={'market_id': (request.data or {}).get('market_id'), 'source': 'research_agent'},
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


class ScanAgentRunView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = ScanRunRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        run = run_scan_agent(source_ids=serializer.validated_data.get('source_ids'), triggered_by='manual_api')
        return Response(SourceScanRunSerializer(run).data, status=status.HTTP_200_OK)


class ScanAgentSignalListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = NarrativeSignalSerializer

    def get_queryset(self):
        status_filter = self.request.query_params.get('status')
        queryset = NarrativeSignal.objects.select_related('linked_market', 'linked_cluster', 'scan_run').order_by('-created_at_scan', '-id')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset[:200]


class ScanAgentClusterListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = NarrativeClusterSerializer

    def get_queryset(self):
        status_filter = self.request.query_params.get('cluster_status')
        queryset = NarrativeCluster.objects.select_related('scan_run').order_by('-item_count', '-last_seen_at', '-id')
        if status_filter:
            queryset = queryset.filter(cluster_status=status_filter)
        return queryset[:200]


class ScanAgentRecommendationListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ScanRecommendationSerializer

    def get_queryset(self):
        recommendation_type = self.request.query_params.get('recommendation_type')
        queryset = ScanRecommendation.objects.select_related('target_signal', 'scan_run').order_by('-created_at_scan', '-id')
        if recommendation_type:
            queryset = queryset.filter(recommendation_type=recommendation_type)
        return queryset[:200]


class ScanAgentSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        latest_run = SourceScanRun.objects.order_by('-started_at', '-id').first()
        payload = {
            'run_count': SourceScanRun.objects.count(),
            'signal_count': NarrativeSignal.objects.count(),
            'shortlisted_signal_count': NarrativeSignal.objects.filter(status='shortlisted').count(),
            'watch_signal_count': NarrativeSignal.objects.filter(status='watch').count(),
            'ignored_signal_count': NarrativeSignal.objects.filter(status='ignore').count(),
            'cluster_count': NarrativeCluster.objects.count(),
            'latest_run': SourceScanRunSerializer(latest_run).data if latest_run else None,
            'latest_recommendations': ScanRecommendationSerializer(
                ScanRecommendation.objects.select_related('target_signal').order_by('-created_at_scan', '-id')[:8],
                many=True,
            ).data,
        }
        return Response(payload, status=status.HTTP_200_OK)


class ScanAgentConsensusRunView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        run = run_consensus_review(triggered_by='manual_api')
        return Response(NarrativeConsensusRunSerializer(run).data, status=status.HTTP_200_OK)


class ScanAgentConsensusRunListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = NarrativeConsensusRunSerializer

    def get_queryset(self):
        return NarrativeConsensusRun.objects.order_by('-started_at', '-id')[:50]


class ScanAgentConsensusRecordListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = NarrativeConsensusRecordSerializer

    def get_queryset(self):
        return NarrativeConsensusRecord.objects.select_related('linked_cluster', 'consensus_run').order_by('-created_at', '-id')[:300]


class ScanAgentConsensusRecordDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = NarrativeConsensusRecordSerializer
    queryset = NarrativeConsensusRecord.objects.select_related('linked_cluster', 'consensus_run')


class ScanAgentDivergenceRecordListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = NarrativeMarketDivergenceRecordSerializer

    def get_queryset(self):
        return NarrativeMarketDivergenceRecord.objects.select_related('linked_market', 'linked_consensus_record').order_by('-created_at', '-id')[:300]


class ScanAgentHandoffPriorityListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ResearchHandoffPrioritySerializer

    def get_queryset(self):
        return ResearchHandoffPriority.objects.select_related('linked_market', 'linked_consensus_record').order_by('-created_at', '-id')[:300]


class ScanAgentHandoffPriorityDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ResearchHandoffPrioritySerializer
    queryset = ResearchHandoffPriority.objects.select_related('linked_market', 'linked_consensus_record')


class ScanAgentConsensusRecommendationListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = NarrativeConsensusRecommendationSerializer

    def get_queryset(self):
        return NarrativeConsensusRecommendation.objects.select_related('target_market', 'target_handoff').order_by('-created_at', '-id')[:300]


class ScanAgentConsensusSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(get_consensus_summary(), status=status.HTTP_200_OK)


class ResearchAgentUniverseScanRunView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = ResearchUniverseRunRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        run = run_market_universe_triage(
            provider_scope=serializer.validated_data.get('provider_scope'),
            source_scope=serializer.validated_data.get('source_scope'),
            triggered_by='manual_api',
        )
        return Response(MarketUniverseRunSerializer(run).data, status=status.HTTP_200_OK)


class ResearchAgentCandidateListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = MarketResearchCandidateSerializer

    def get_queryset(self):
        queryset = MarketResearchCandidate.objects.select_related('linked_market', 'universe_run').order_by('-created_at', '-id')
        status_filter = self.request.query_params.get('status')
        provider_filter = self.request.query_params.get('provider')
        category_filter = self.request.query_params.get('category')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if provider_filter:
            queryset = queryset.filter(market_provider=provider_filter)
        if category_filter:
            queryset = queryset.filter(category=category_filter)
        return queryset[:300]


class ResearchAgentTriageDecisionListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = MarketTriageDecisionV2Serializer

    def get_queryset(self):
        return MarketTriageDecisionV2.objects.select_related('linked_candidate').order_by('-created_at', '-id')[:300]


class ResearchAgentRecommendationListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = MarketResearchRecommendationSerializer

    def get_queryset(self):
        recommendation_filter = self.request.query_params.get('recommendation_type')
        queryset = MarketResearchRecommendation.objects.select_related('target_candidate', 'target_market').order_by('-created_at', '-id')
        if recommendation_filter:
            queryset = queryset.filter(recommendation_type=recommendation_filter)
        return queryset[:300]


class ResearchAgentUniverseSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(get_latest_universe_summary(), status=status.HTTP_200_OK)


class ResearchAgentRunPursuitReviewView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RunPursuitReviewRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        run = run_pursuit_review(market_limit=serializer.validated_data['market_limit'], triggered_by='manual_api')
        return Response(ResearchPursuitRunSerializer(run).data, status=status.HTTP_200_OK)


class ResearchAgentPursuitRunListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ResearchPursuitRunSerializer

    def get_queryset(self):
        return ResearchPursuitRun.objects.order_by('-started_at', '-id')[:50]


class ResearchAgentStructuralAssessmentListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ResearchStructuralAssessmentSerializer

    def get_queryset(self):
        queryset = ResearchStructuralAssessment.objects.select_related('linked_market', 'linked_handoff_priority').order_by('-created_at', '-id')
        run_id = self.request.query_params.get('run_id')
        if run_id:
            queryset = queryset.filter(pursuit_run_id=run_id)
        return queryset[:300]


class ResearchAgentPursuitScoreListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ResearchPursuitScoreSerializer

    def get_queryset(self):
        queryset = ResearchPursuitScore.objects.select_related('linked_market', 'linked_assessment').order_by('-created_at', '-id')
        run_id = self.request.query_params.get('run_id')
        if run_id:
            queryset = queryset.filter(pursuit_run_id=run_id)
        return queryset[:300]


class ResearchAgentPredictionHandoffListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PredictionHandoffCandidateSerializer

    def get_queryset(self):
        queryset = PredictionHandoffCandidate.objects.select_related('linked_market', 'linked_pursuit_score').order_by('-created_at', '-id')
        run_id = self.request.query_params.get('run_id')
        if run_id:
            queryset = queryset.filter(pursuit_run_id=run_id)
        return queryset[:300]


class ResearchAgentPursuitRecommendationListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ResearchPursuitRecommendationSerializer

    def get_queryset(self):
        queryset = ResearchPursuitRecommendation.objects.select_related('target_market', 'target_assessment').order_by('-created_at', '-id')
        run_id = self.request.query_params.get('run_id')
        if run_id:
            queryset = queryset.filter(pursuit_run_id=run_id)
        return queryset[:300]


class ResearchAgentPursuitSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(get_latest_pursuit_summary(), status=status.HTTP_200_OK)
