from django.urls import path

from apps.tuning_board.views import (
    TuningBundleListView,
    TuningHypothesisListView,
    TuningProposalListView,
    TuningRecommendationListView,
    TuningRunReviewView,
    TuningSummaryView,
)

urlpatterns = [
    path('run-review/', TuningRunReviewView.as_view(), name='run-review'),
    path('proposals/', TuningProposalListView.as_view(), name='proposals'),
    path('hypotheses/', TuningHypothesisListView.as_view(), name='hypotheses'),
    path('recommendations/', TuningRecommendationListView.as_view(), name='recommendations'),
    path('summary/', TuningSummaryView.as_view(), name='summary'),
    path('bundles/', TuningBundleListView.as_view(), name='bundles'),
]
