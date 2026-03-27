from django.db.models import Count
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.research_agent.models import (
    MarketUniverseScanRun,
    NarrativeItem,
    NarrativeSource,
    NarrativeSourceType,
    PursuitCandidate,
    ResearchCandidate,
    ResearchScanRun,
)
from apps.research_agent.serializers import (
    MarketUniverseScanRunSerializer,
    NarrativeItemSerializer,
    NarrativeSourceCreateSerializer,
    NarrativeSourceSerializer,
    PursuitCandidateSerializer,
    ResearchCandidateSerializer,
    ResearchRunRequestSerializer,
    ResearchScanRunSerializer,
    TriageToPredictionRequestSerializer,
    UniverseScanRunRequestSerializer,
)
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
