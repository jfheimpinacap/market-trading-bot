from django.urls import path

from apps.autonomy_seed.views import (
    AutonomySeedAcknowledgeView,
    AutonomySeedCandidatesView,
    AutonomySeedListView,
    AutonomySeedRecommendationsView,
    AutonomySeedRegisterView,
    AutonomySeedRunReviewView,
    AutonomySeedSummaryView,
)

app_name = 'autonomy_seed'

urlpatterns = [
    path('candidates/', AutonomySeedCandidatesView.as_view(), name='candidates'),
    path('run-review/', AutonomySeedRunReviewView.as_view(), name='run_review'),
    path('seeds/', AutonomySeedListView.as_view(), name='seeds'),
    path('recommendations/', AutonomySeedRecommendationsView.as_view(), name='recommendations'),
    path('summary/', AutonomySeedSummaryView.as_view(), name='summary'),
    path('register/<int:package_id>/', AutonomySeedRegisterView.as_view(), name='register'),
    path('acknowledge/<int:seed_id>/', AutonomySeedAcknowledgeView.as_view(), name='acknowledge'),
]
