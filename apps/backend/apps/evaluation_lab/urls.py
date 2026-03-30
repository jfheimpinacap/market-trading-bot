from django.urls import path

from apps.evaluation_lab.views import (
    CalibrationBucketDetailView,
    CalibrationBucketListView,
    EffectivenessMetricDetailView,
    EffectivenessMetricListView,
    EvaluationBuildForSessionView,
    EvaluationComparisonView,
    EvaluationRecommendationListView,
    EvaluationRecentView,
    EvaluationRunDetailView,
    EvaluationRunListView,
    EvaluationSummaryView,
    OutcomeAlignmentListView,
    RuntimeEvaluationRunView,
    RuntimeEvaluationSummaryView,
)

urlpatterns = [
    path('summary/', EvaluationSummaryView.as_view(), name='summary'),
    path('runs/', EvaluationRunListView.as_view(), name='run-list'),
    path('runs/<int:pk>/', EvaluationRunDetailView.as_view(), name='run-detail'),
    path('build-for-session/<int:session_id>/', EvaluationBuildForSessionView.as_view(), name='build-for-session'),
    path('recent/', EvaluationRecentView.as_view(), name='recent'),
    path('comparison/', EvaluationComparisonView.as_view(), name='comparison'),
    path('run-runtime-evaluation/', RuntimeEvaluationRunView.as_view(), name='run-runtime-evaluation'),
    path('outcome-alignment/', OutcomeAlignmentListView.as_view(), name='outcome-alignment'),
    path('calibration-buckets/', CalibrationBucketListView.as_view(), name='calibration-buckets'),
    path('calibration-buckets/<int:pk>/', CalibrationBucketDetailView.as_view(), name='calibration-buckets-detail'),
    path('effectiveness-metrics/', EffectivenessMetricListView.as_view(), name='effectiveness-metrics'),
    path('effectiveness-metrics/<int:pk>/', EffectivenessMetricDetailView.as_view(), name='effectiveness-metric-detail'),
    path('recommendations/', EvaluationRecommendationListView.as_view(), name='recommendations'),
    path('runtime-summary/', RuntimeEvaluationSummaryView.as_view(), name='runtime-summary'),
]
