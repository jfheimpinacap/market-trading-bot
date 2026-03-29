from django.urls import path

from apps.autonomy_backlog.views import (
    AutonomyBacklogCandidatesView,
    AutonomyBacklogCreateView,
    AutonomyBacklogDeferView,
    AutonomyBacklogItemsView,
    AutonomyBacklogPrioritizeView,
    AutonomyBacklogRecommendationsView,
    AutonomyBacklogRunReviewView,
    AutonomyBacklogSummaryView,
)

app_name = 'autonomy_backlog'

urlpatterns = [
    path('candidates/', AutonomyBacklogCandidatesView.as_view(), name='candidates'),
    path('run-review/', AutonomyBacklogRunReviewView.as_view(), name='run_review'),
    path('items/', AutonomyBacklogItemsView.as_view(), name='items'),
    path('recommendations/', AutonomyBacklogRecommendationsView.as_view(), name='recommendations'),
    path('summary/', AutonomyBacklogSummaryView.as_view(), name='summary'),
    path('create/<int:artifact_id>/', AutonomyBacklogCreateView.as_view(), name='create'),
    path('prioritize/<int:item_id>/', AutonomyBacklogPrioritizeView.as_view(), name='prioritize'),
    path('defer/<int:item_id>/', AutonomyBacklogDeferView.as_view(), name='defer'),
]
