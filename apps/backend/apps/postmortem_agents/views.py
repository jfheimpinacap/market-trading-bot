from django.db.models import Avg, Count
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.postmortem_agents.models import PostmortemAgentReview, PostmortemBoardConclusion, PostmortemBoardRun
from apps.memory_retrieval.models import MemoryQueryType
from apps.memory_retrieval.services import retrieve_precedents
from apps.postmortem_agents.serializers import (
    PostmortemAgentReviewSerializer,
    PostmortemBoardConclusionSerializer,
    PostmortemBoardRunRequestSerializer,
    PostmortemBoardRunSerializer,
)
from apps.postmortem_agents.services.board import run_postmortem_board


class PostmortemBoardRunApiView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = PostmortemBoardRunRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        result = run_postmortem_board(
            related_trade_review_id=serializer.validated_data['related_trade_review_id'],
            force_learning_rebuild=serializer.validated_data.get('force_learning_rebuild', False),
        )
        return Response(PostmortemBoardRunSerializer(result.board_run).data, status=status.HTTP_200_OK)


class PostmortemBoardRunListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PostmortemBoardRunSerializer

    def get_queryset(self):
        queryset = PostmortemBoardRun.objects.select_related('related_trade_review', 'related_trade_review__paper_trade').order_by('-created_at', '-id')
        review_id = self.request.query_params.get('related_trade_review_id')
        if review_id:
            queryset = queryset.filter(related_trade_review_id=review_id)
        return queryset[:200]


class PostmortemBoardRunDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PostmortemBoardRunSerializer
    queryset = PostmortemBoardRun.objects.select_related('related_trade_review').order_by('-created_at', '-id')


class PostmortemBoardReviewListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PostmortemAgentReviewSerializer

    def get_queryset(self):
        queryset = PostmortemAgentReview.objects.select_related('board_run').order_by('-created_at', '-id')
        board_run_id = self.request.query_params.get('board_run_id')
        if board_run_id:
            queryset = queryset.filter(board_run_id=board_run_id)
        return queryset[:500]


class PostmortemBoardConclusionListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PostmortemBoardConclusionSerializer

    def get_queryset(self):
        queryset = PostmortemBoardConclusion.objects.select_related('board_run').order_by('-created_at', '-id')
        board_run_id = self.request.query_params.get('board_run_id')
        if board_run_id:
            queryset = queryset.filter(board_run_id=board_run_id)
        return queryset[:200]


class PostmortemBoardSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        runs = PostmortemBoardRun.objects.all()
        payload = {
            'total_runs': runs.count(),
            'runs_by_status': {item['status']: item['total'] for item in runs.values('status').annotate(total=Count('id'))},
            'average_perspectives': runs.aggregate(v=Avg('perspectives_run_count'))['v'],
            'latest_run': PostmortemBoardRunSerializer(runs.order_by('-created_at', '-id').first()).data if runs.exists() else None,
            'total_reviews': PostmortemAgentReview.objects.count(),
            'total_conclusions': PostmortemBoardConclusion.objects.count(),
        }
        return Response(payload, status=status.HTTP_200_OK)


class PostmortemPrecedentCompareView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        query_text = (request.data or {}).get('query_text')
        if not query_text:
            return Response({'detail': 'query_text is required.'}, status=status.HTTP_400_BAD_REQUEST)
        run = retrieve_precedents(
            query_text=query_text,
            query_type=MemoryQueryType.POSTMORTEM,
            context_metadata={'review_id': (request.data or {}).get('review_id'), 'source': 'postmortem_agents'},
            limit=min(int((request.data or {}).get('limit', 6)), 12),
        )
        return Response({'retrieval_run_id': run.id, 'result_count': run.result_count}, status=status.HTTP_200_OK)
