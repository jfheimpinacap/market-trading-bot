from django.urls import path

from apps.prediction_agent.views import (
    PredictionBuildFeaturesView,
    PredictionProfileListView,
    PredictionRunRuntimeReviewView,
    PredictionRuntimeAssessmentDetailView,
    PredictionRuntimeAssessmentListView,
    PredictionRuntimeCandidateListView,
    PredictionRuntimeRecommendationListView,
    PredictionRuntimeSummaryView,
    PredictionScoreDetailView,
    PredictionScoreListView,
    PredictionScoreMarketView,
    PredictionSummaryView,
    PredictionPrecedentAssistView,
)

app_name = 'prediction_agent'

urlpatterns = [
    path('profiles/', PredictionProfileListView.as_view(), name='profile-list'),
    path('score-market/', PredictionScoreMarketView.as_view(), name='score-market'),
    path('scores/', PredictionScoreListView.as_view(), name='score-list'),
    path('scores/<int:pk>/', PredictionScoreDetailView.as_view(), name='score-detail'),
    path('summary/', PredictionSummaryView.as_view(), name='summary'),
    path('build-features/', PredictionBuildFeaturesView.as_view(), name='build-features'),
    path('precedent-assist/', PredictionPrecedentAssistView.as_view(), name='precedent-assist'),
    path('run-runtime-review/', PredictionRunRuntimeReviewView.as_view(), name='run-runtime-review'),
    path('runtime-candidates/', PredictionRuntimeCandidateListView.as_view(), name='runtime-candidates'),
    path('runtime-assessments/', PredictionRuntimeAssessmentListView.as_view(), name='runtime-assessments'),
    path('runtime-assessments/<int:pk>/', PredictionRuntimeAssessmentDetailView.as_view(), name='runtime-assessment-detail'),
    path('runtime-recommendations/', PredictionRuntimeRecommendationListView.as_view(), name='runtime-recommendations'),
    path('runtime-summary/', PredictionRuntimeSummaryView.as_view(), name='runtime-summary'),
]
