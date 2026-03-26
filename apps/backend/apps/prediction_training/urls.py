from django.urls import path

from apps.prediction_training.views import (
    ActiveModelRecommendationView,
    ModelComparisonCreateView,
    ModelComparisonDetailView,
    ModelComparisonListView,
    ModelEvaluationProfileListView,
    ModelGovernanceSummaryView,
    PredictionActiveModelView,
    PredictionBuildDatasetView,
    PredictionModelActivateView,
    PredictionModelListView,
    PredictionTrainRunCreateView,
    PredictionTrainRunDetailView,
    PredictionTrainRunListView,
    PredictionTrainSummaryView,
)

app_name = 'prediction_training'

urlpatterns = [
    path('train/build-dataset/', PredictionBuildDatasetView.as_view(), name='build-dataset'),
    path('train/run/', PredictionTrainRunCreateView.as_view(), name='train-run'),
    path('train/runs/', PredictionTrainRunListView.as_view(), name='train-run-list'),
    path('train/runs/<int:pk>/', PredictionTrainRunDetailView.as_view(), name='train-run-detail'),
    path('train/summary/', PredictionTrainSummaryView.as_view(), name='train-summary'),
    path('models/', PredictionModelListView.as_view(), name='model-list'),
    path('models/active/', PredictionActiveModelView.as_view(), name='model-active'),
    path('models/<int:pk>/activate/', PredictionModelActivateView.as_view(), name='model-activate'),
    path('model-profiles/', ModelEvaluationProfileListView.as_view(), name='model-profiles'),
    path('compare-models/', ModelComparisonCreateView.as_view(), name='compare-models'),
    path('comparisons/', ModelComparisonListView.as_view(), name='comparisons'),
    path('comparisons/<int:pk>/', ModelComparisonDetailView.as_view(), name='comparison-detail'),
    path('active-model-recommendation/', ActiveModelRecommendationView.as_view(), name='active-model-recommendation'),
    path('model-governance-summary/', ModelGovernanceSummaryView.as_view(), name='model-governance-summary'),
]
