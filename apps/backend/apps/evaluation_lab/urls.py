from django.urls import path

from apps.evaluation_lab.views import (
    EvaluationBuildForSessionView,
    EvaluationComparisonView,
    EvaluationRecentView,
    EvaluationRunDetailView,
    EvaluationRunListView,
    EvaluationSummaryView,
)

urlpatterns = [
    path('summary/', EvaluationSummaryView.as_view(), name='summary'),
    path('runs/', EvaluationRunListView.as_view(), name='run-list'),
    path('runs/<int:pk>/', EvaluationRunDetailView.as_view(), name='run-detail'),
    path('build-for-session/<int:session_id>/', EvaluationBuildForSessionView.as_view(), name='build-for-session'),
    path('recent/', EvaluationRecentView.as_view(), name='recent'),
    path('comparison/', EvaluationComparisonView.as_view(), name='comparison'),
]
