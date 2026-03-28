from django.urls import path

from apps.autonomy_manager.views import (
    AutonomyDomainsView,
    AutonomyRecommendationsView,
    AutonomyReviewRunView,
    AutonomyStageStatesView,
    AutonomySummaryView,
    AutonomyTransitionApplyView,
    AutonomyTransitionRollbackView,
)

urlpatterns = [
    path('domains/', AutonomyDomainsView.as_view(), name='domains'),
    path('states/', AutonomyStageStatesView.as_view(), name='states'),
    path('recommendations/', AutonomyRecommendationsView.as_view(), name='recommendations'),
    path('run-review/', AutonomyReviewRunView.as_view(), name='run-review'),
    path('transitions/<int:pk>/apply/', AutonomyTransitionApplyView.as_view(), name='transition-apply'),
    path('transitions/<int:pk>/rollback/', AutonomyTransitionRollbackView.as_view(), name='transition-rollback'),
    path('summary/', AutonomySummaryView.as_view(), name='summary'),
]
