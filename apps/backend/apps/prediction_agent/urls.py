from django.urls import path

from apps.prediction_agent.views import (
    PredictionBuildFeaturesView,
    PredictionProfileListView,
    PredictionScoreDetailView,
    PredictionScoreListView,
    PredictionScoreMarketView,
    PredictionSummaryView,
)

app_name = 'prediction_agent'

urlpatterns = [
    path('profiles/', PredictionProfileListView.as_view(), name='profile-list'),
    path('score-market/', PredictionScoreMarketView.as_view(), name='score-market'),
    path('scores/', PredictionScoreListView.as_view(), name='score-list'),
    path('scores/<int:pk>/', PredictionScoreDetailView.as_view(), name='score-detail'),
    path('summary/', PredictionSummaryView.as_view(), name='summary'),
    path('build-features/', PredictionBuildFeaturesView.as_view(), name='build-features'),
]
