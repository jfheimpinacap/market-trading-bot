from django.db.models import Count
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.research_agent.models import NarrativeItem, NarrativeSource, NarrativeSourceType, ResearchCandidate, ResearchScanRun
from apps.research_agent.serializers import (
    NarrativeItemSerializer,
    NarrativeSourceCreateSerializer,
    NarrativeSourceSerializer,
    ResearchCandidateSerializer,
    ResearchRunRequestSerializer,
    ResearchScanRunSerializer,
)
from apps.research_agent.services.analyze import run_narrative_analysis
from apps.research_agent.services.scan import run_full_research_scan, run_research_scan


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


class ResearchSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        latest_run = ResearchScanRun.objects.order_by('-started_at', '-id').first()
        payload = {
            'source_count': NarrativeSource.objects.filter(is_enabled=True).count(),
            'rss_source_count': NarrativeSource.objects.filter(is_enabled=True, source_type=NarrativeSourceType.RSS).count(),
            'reddit_source_count': NarrativeSource.objects.filter(is_enabled=True, source_type=NarrativeSourceType.REDDIT).count(),
            'item_count': NarrativeItem.objects.count(),
            'rss_item_count': NarrativeItem.objects.filter(source__source_type=NarrativeSourceType.RSS).count(),
            'reddit_item_count': NarrativeItem.objects.filter(source__source_type=NarrativeSourceType.REDDIT).count(),
            'analyzed_count': NarrativeItem.objects.filter(analysis__isnull=False).count(),
            'candidate_count': ResearchCandidate.objects.count(),
            'mixed_candidate_count': ResearchCandidate.objects.filter(source_mix__in=['mixed', 'social_heavy', 'news_confirmed']).count(),
            'latest_run': ResearchScanRunSerializer(latest_run).data if latest_run else None,
        }
        return Response(payload, status=status.HTTP_200_OK)
