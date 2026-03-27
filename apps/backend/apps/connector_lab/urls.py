from django.urls import path

from apps.connector_lab.views import (
    ConnectorCasesView,
    ConnectorCurrentReadinessView,
    ConnectorRunDetailView,
    ConnectorRunQualificationView,
    ConnectorRunsView,
    ConnectorSummaryView,
)

app_name = 'connector_lab'

urlpatterns = [
    path('cases/', ConnectorCasesView.as_view(), name='cases'),
    path('run-qualification/', ConnectorRunQualificationView.as_view(), name='run-qualification'),
    path('runs/', ConnectorRunsView.as_view(), name='runs'),
    path('runs/<int:pk>/', ConnectorRunDetailView.as_view(), name='run-detail'),
    path('current-readiness/', ConnectorCurrentReadinessView.as_view(), name='current-readiness'),
    path('summary/', ConnectorSummaryView.as_view(), name='summary'),
]
