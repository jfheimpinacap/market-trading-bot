from django.urls import path

from apps.autonomy_intervention.views import (
    InterventionActionsView,
    InterventionCreateRequestView,
    InterventionExecuteRequestView,
    InterventionRequestsView,
    InterventionRunReviewView,
    InterventionSummaryView,
)

app_name = 'autonomy_intervention'

urlpatterns = [
    path('requests/', InterventionRequestsView.as_view(), name='requests'),
    path('run-review/', InterventionRunReviewView.as_view(), name='run_review'),
    path('summary/', InterventionSummaryView.as_view(), name='summary'),
    path('request/<int:campaign_id>/', InterventionCreateRequestView.as_view(), name='create_request'),
    path('execute/<int:request_id>/', InterventionExecuteRequestView.as_view(), name='execute_request'),
    path('actions/', InterventionActionsView.as_view(), name='actions'),
]
