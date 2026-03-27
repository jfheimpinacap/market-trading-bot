from django.db.models import Avg, Count
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.markets.models import Market
from apps.prediction_agent.models import PredictionModelProfile, PredictionScore
from apps.prediction_agent.serializers import (
    PredictionModelProfileSerializer,
    PredictionScoreRequestSerializer,
    PredictionScoreSerializer,
)
from apps.prediction_agent.services.features import build_prediction_features
from apps.prediction_agent.services.profiles import ensure_default_prediction_profiles
from apps.prediction_agent.services.scoring import score_market_prediction
from apps.memory_retrieval.models import MemoryQueryType
from apps.memory_retrieval.services import retrieve_precedents


class PredictionProfileListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PredictionModelProfileSerializer

    def get_queryset(self):
        ensure_default_prediction_profiles()
        return PredictionModelProfile.objects.filter(is_active=True).order_by('slug')


class PredictionScoreMarketView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = PredictionScoreRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)

        market = Market.objects.filter(id=serializer.validated_data['market_id']).first()
        if market is None:
            return Response({'detail': 'Market not found.'}, status=status.HTTP_404_NOT_FOUND)

        result = score_market_prediction(
            market=market,
            profile_slug=serializer.validated_data.get('profile_slug') or None,
            triggered_by=serializer.validated_data.get('triggered_by', 'api'),
        )
        return Response(PredictionScoreSerializer(result.score).data, status=status.HTTP_201_CREATED)


class PredictionScoreListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PredictionScoreSerializer

    def get_queryset(self):
        queryset = PredictionScore.objects.select_related('market', 'model_profile', 'run').order_by('-created_at', '-id')
        market_id = self.request.query_params.get('market_id')
        profile_slug = self.request.query_params.get('profile_slug')
        if market_id:
            queryset = queryset.filter(market_id=market_id)
        if profile_slug:
            queryset = queryset.filter(model_profile__slug=profile_slug)
        return queryset[:200]


class PredictionScoreDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PredictionScoreSerializer
    queryset = PredictionScore.objects.select_related('market', 'model_profile', 'run').order_by('-created_at', '-id')


class PredictionSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        ensure_default_prediction_profiles()
        latest_score = PredictionScore.objects.select_related('market', 'model_profile').order_by('-created_at', '-id').first()
        aggregate = PredictionScore.objects.aggregate(
            total_scores=Count('id'),
            avg_edge=Avg('edge'),
            avg_confidence=Avg('confidence'),
        )
        payload = {
            'profile_count': PredictionModelProfile.objects.filter(is_active=True).count(),
            'total_scores': aggregate['total_scores'] or 0,
            'avg_edge': aggregate['avg_edge'],
            'avg_confidence': aggregate['avg_confidence'],
            'latest_score': PredictionScoreSerializer(latest_score).data if latest_score else None,
        }
        return Response(payload, status=status.HTTP_200_OK)


class PredictionBuildFeaturesView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        market_id = request.data.get('market_id')
        market = Market.objects.filter(id=market_id).first()
        if market is None:
            return Response({'detail': 'Market not found.'}, status=status.HTTP_404_NOT_FOUND)
        result = build_prediction_features(market=market)
        return Response(
            {
                'market_id': market.id,
                'market_slug': market.slug,
                'stale_market_data': result.stale_market_data,
                'feature_snapshot': result.snapshot,
            },
            status=status.HTTP_200_OK,
        )


class PredictionPrecedentAssistView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        query_text = (request.data or {}).get('query_text')
        if not query_text:
            return Response({'detail': 'query_text is required.'}, status=status.HTTP_400_BAD_REQUEST)
        run = retrieve_precedents(
            query_text=query_text,
            query_type=MemoryQueryType.PREDICTION,
            context_metadata={'market_id': (request.data or {}).get('market_id'), 'source': 'prediction_agent'},
            limit=min(int((request.data or {}).get('limit', 6)), 12),
        )
        return Response({'retrieval_run_id': run.id, 'result_count': run.result_count}, status=status.HTTP_200_OK)
