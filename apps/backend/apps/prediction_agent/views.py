from django.db.models import Avg, Count
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.markets.models import Market
from apps.prediction_agent.models import (
    PredictionModelProfile,
    PredictionRuntimeAssessment,
    PredictionRuntimeCandidate,
    PredictionRuntimeRecommendation,
    PredictionRuntimeRun,
    PredictionScore,
    PredictionIntakeRun,
    PredictionIntakeCandidate,
    PredictionConvictionReview,
    RiskReadyPredictionHandoff,
    PredictionIntakeRecommendation,
)
from apps.prediction_agent.serializers import (
    PredictionModelProfileSerializer,
    PredictionRuntimeAssessmentSerializer,
    PredictionRuntimeCandidateSerializer,
    PredictionRuntimeRecommendationSerializer,
    PredictionRuntimeReviewRequestSerializer,
    PredictionRuntimeRunSerializer,
    PredictionScoreRequestSerializer,
    PredictionScoreSerializer,
    PredictionIntakeRunSerializer,
    PredictionIntakeCandidateSerializer,
    PredictionConvictionReviewSerializer,
    RiskReadyPredictionHandoffSerializer,
    PredictionIntakeRecommendationSerializer,
)
from apps.prediction_agent.services.features import build_prediction_features
from apps.prediction_agent.services.profiles import ensure_default_prediction_profiles
from apps.prediction_agent.services.run import run_prediction_intake_review, run_prediction_runtime_review
from apps.prediction_agent.services.scoring import score_market_prediction
from apps.memory_retrieval.models import MemoryQueryType
from apps.memory_retrieval.services import run_assist


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
        run = run_assist(
            query_text=query_text,
            query_type=MemoryQueryType.PREDICTION,
            context_metadata={'market_id': (request.data or {}).get('market_id'), 'source': 'prediction_agent'},
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


class PredictionRunRuntimeReviewView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = PredictionRuntimeReviewRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        result = run_prediction_runtime_review(triggered_by=serializer.validated_data.get('triggered_by', 'manual'))
        return Response(PredictionRuntimeRunSerializer(result.runtime_run).data, status=status.HTTP_201_CREATED)


class PredictionRuntimeCandidateListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PredictionRuntimeCandidateSerializer

    def get_queryset(self):
        queryset = PredictionRuntimeCandidate.objects.select_related('linked_market', 'linked_research_candidate', 'runtime_run')
        run_id = self.request.query_params.get('run_id')
        if run_id:
            queryset = queryset.filter(runtime_run_id=run_id)
        return queryset.order_by('-created_at', '-id')[:200]


class PredictionRuntimeAssessmentListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PredictionRuntimeAssessmentSerializer

    def get_queryset(self):
        queryset = PredictionRuntimeAssessment.objects.select_related('linked_candidate__linked_market', 'linked_candidate__runtime_run')
        status_code = self.request.query_params.get('status')
        if status_code:
            queryset = queryset.filter(prediction_status=status_code)
        run_id = self.request.query_params.get('run_id')
        if run_id:
            queryset = queryset.filter(linked_candidate__runtime_run_id=run_id)
        return queryset.order_by('-created_at', '-id')[:200]


class PredictionRuntimeAssessmentDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PredictionRuntimeAssessmentSerializer
    queryset = PredictionRuntimeAssessment.objects.select_related('linked_candidate__linked_market', 'linked_candidate__runtime_run')


class PredictionRuntimeRecommendationListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PredictionRuntimeRecommendationSerializer

    def get_queryset(self):
        queryset = PredictionRuntimeRecommendation.objects.select_related(
            'runtime_run',
            'target_assessment__linked_candidate__linked_market',
        )
        recommendation_type = self.request.query_params.get('recommendation_type')
        if recommendation_type:
            queryset = queryset.filter(recommendation_type=recommendation_type)
        run_id = self.request.query_params.get('run_id')
        if run_id:
            queryset = queryset.filter(runtime_run_id=run_id)
        return queryset.order_by('-created_at', '-id')[:200]


class PredictionRuntimeSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        latest_run = PredictionRuntimeRun.objects.order_by('-started_at', '-id').first()
        if latest_run is None:
            return Response(
                {
                    'latest_run': None,
                    'status_counts': {},
                    'recommendation_counts': {},
                    'model_mode_counts': {},
                },
                status=status.HTTP_200_OK,
            )

        assessments = PredictionRuntimeAssessment.objects.filter(linked_candidate__runtime_run=latest_run)
        recommendations = PredictionRuntimeRecommendation.objects.filter(runtime_run=latest_run)
        status_counts = {row['prediction_status']: row['count'] for row in assessments.values('prediction_status').annotate(count=Count('id'))}
        recommendation_counts = {
            row['recommendation_type']: row['count']
            for row in recommendations.values('recommendation_type').annotate(count=Count('id'))
        }
        model_mode_counts = {row['model_mode']: row['count'] for row in assessments.values('model_mode').annotate(count=Count('id'))}
        payload = {
            'latest_run': PredictionRuntimeRunSerializer(latest_run).data,
            'status_counts': status_counts,
            'recommendation_counts': recommendation_counts,
            'model_mode_counts': model_mode_counts,
        }
        return Response(payload, status=status.HTTP_200_OK)


class PredictionRunIntakeReviewView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = PredictionRuntimeReviewRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        result = run_prediction_intake_review(triggered_by=serializer.validated_data.get('triggered_by', 'manual'))
        return Response(PredictionIntakeRunSerializer(result.intake_run).data, status=status.HTTP_201_CREATED)


class PredictionIntakeRunListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PredictionIntakeRunSerializer

    def get_queryset(self):
        return PredictionIntakeRun.objects.order_by('-created_at', '-id')[:100]


class PredictionIntakeCandidateListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PredictionIntakeCandidateSerializer

    def get_queryset(self):
        queryset = PredictionIntakeCandidate.objects.select_related('linked_market', 'intake_run').order_by('-created_at', '-id')
        run_id = self.request.query_params.get('run_id')
        if run_id:
            queryset = queryset.filter(intake_run_id=run_id)
        return queryset[:200]


class PredictionConvictionReviewListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PredictionConvictionReviewSerializer

    def get_queryset(self):
        queryset = PredictionConvictionReview.objects.select_related('linked_intake_candidate__linked_market').order_by('-created_at', '-id')
        run_id = self.request.query_params.get('run_id')
        if run_id:
            queryset = queryset.filter(linked_intake_candidate__intake_run_id=run_id)
        return queryset[:200]


class PredictionRiskHandoffListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = RiskReadyPredictionHandoffSerializer

    def get_queryset(self):
        queryset = RiskReadyPredictionHandoff.objects.select_related('linked_market', 'linked_conviction_review').order_by('-created_at', '-id')
        run_id = self.request.query_params.get('run_id')
        if run_id:
            queryset = queryset.filter(linked_conviction_review__linked_intake_candidate__intake_run_id=run_id)
        return queryset[:200]


class PredictionIntakeRecommendationListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PredictionIntakeRecommendationSerializer

    def get_queryset(self):
        queryset = PredictionIntakeRecommendation.objects.select_related('target_market', 'intake_run').order_by('-created_at', '-id')
        run_id = self.request.query_params.get('run_id')
        if run_id:
            queryset = queryset.filter(intake_run_id=run_id)
        return queryset[:200]


class PredictionIntakeSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        latest_run = PredictionIntakeRun.objects.order_by('-started_at', '-id').first()
        if latest_run is None:
            return Response({'latest_run': None, 'review_status_counts': {}, 'handoff_status_counts': {}, 'recommendation_counts': {}}, status=status.HTTP_200_OK)

        reviews = PredictionConvictionReview.objects.filter(linked_intake_candidate__intake_run=latest_run)
        handoffs = RiskReadyPredictionHandoff.objects.filter(linked_conviction_review__linked_intake_candidate__intake_run=latest_run)
        recommendations = PredictionIntakeRecommendation.objects.filter(intake_run=latest_run)

        payload = {
            'latest_run': PredictionIntakeRunSerializer(latest_run).data,
            'review_status_counts': {row['review_status']: row['count'] for row in reviews.values('review_status').annotate(count=Count('id'))},
            'handoff_status_counts': {row['handoff_status']: row['count'] for row in handoffs.values('handoff_status').annotate(count=Count('id'))},
            'recommendation_counts': {row['recommendation_type']: row['count'] for row in recommendations.values('recommendation_type').annotate(count=Count('id'))},
        }
        return Response(payload, status=status.HTTP_200_OK)
