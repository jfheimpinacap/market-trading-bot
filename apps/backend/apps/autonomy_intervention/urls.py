from django.urls import path

from apps.autonomy_intervention.views import (
    AutonomyInterventionActionsView,
    AutonomyInterventionCancelRequestView,
    AutonomyInterventionCreateRequestView,
    AutonomyInterventionExecuteRequestView,
    AutonomyInterventionRequestDetailView,
    AutonomyInterventionRequestsView,
    AutonomyInterventionRunReviewView,
    AutonomyInterventionSummaryView,
)

app_name = 'autonomy_intervention'

urlpatterns = [
    path('requests/', AutonomyInterventionRequestsView.as_view(), name='requests'),
    path('requests/<int:request_id>/', AutonomyInterventionRequestDetailView.as_view(), name='request_detail'),
    path('run-review/', AutonomyInterventionRunReviewView.as_view(), name='run_review'),
    path('summary/', AutonomyInterventionSummaryView.as_view(), name='summary'),
    path('request/<int:campaign_id>/', AutonomyInterventionCreateRequestView.as_view(), name='create_request'),
    path('execute/<int:request_id>/', AutonomyInterventionExecuteRequestView.as_view(), name='execute_request'),
    path('cancel/<int:request_id>/', AutonomyInterventionCancelRequestView.as_view(), name='cancel_request'),
    path('actions/', AutonomyInterventionActionsView.as_view(), name='actions'),
]
