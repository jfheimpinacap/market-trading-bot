from django.urls import path

from apps.autonomy_operations.views import (
    AutonomyOperationsAcknowledgeSignalView,
    AutonomyOperationsRecommendationsView,
    AutonomyOperationsRunMonitorView,
    AutonomyOperationsRuntimeDetailView,
    AutonomyOperationsRuntimeView,
    AutonomyOperationsSignalsView,
    AutonomyOperationsSummaryView,
)

app_name = 'autonomy_operations'

urlpatterns = [
    path('runtime/', AutonomyOperationsRuntimeView.as_view(), name='runtime'),
    path('runtime/<int:campaign_id>/', AutonomyOperationsRuntimeDetailView.as_view(), name='runtime_detail'),
    path('run-monitor/', AutonomyOperationsRunMonitorView.as_view(), name='run_monitor'),
    path('signals/', AutonomyOperationsSignalsView.as_view(), name='signals'),
    path('signals/<int:signal_id>/acknowledge/', AutonomyOperationsAcknowledgeSignalView.as_view(), name='acknowledge_signal'),
    path('recommendations/', AutonomyOperationsRecommendationsView.as_view(), name='recommendations'),
    path('summary/', AutonomyOperationsSummaryView.as_view(), name='summary'),
]
