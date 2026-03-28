from django.urls import path

from apps.autonomy_program.views import (
    AutonomyProgramHealthView,
    AutonomyProgramRecommendationsView,
    AutonomyProgramRulesView,
    AutonomyProgramRunReviewView,
    AutonomyProgramStateView,
    AutonomyProgramSummaryView,
)

app_name = 'autonomy_program'

urlpatterns = [
    path('state/', AutonomyProgramStateView.as_view(), name='state'),
    path('rules/', AutonomyProgramRulesView.as_view(), name='rules'),
    path('run-review/', AutonomyProgramRunReviewView.as_view(), name='run_review'),
    path('recommendations/', AutonomyProgramRecommendationsView.as_view(), name='recommendations'),
    path('health/', AutonomyProgramHealthView.as_view(), name='health'),
    path('summary/', AutonomyProgramSummaryView.as_view(), name='summary'),
]
