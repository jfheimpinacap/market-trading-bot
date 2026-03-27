from django.urls import path

from apps.execution_venue.views import (
    ExecutionVenueBuildPayloadView,
    ExecutionVenueCapabilitiesView,
    ExecutionVenueDryRunView,
    ExecutionVenueParityRunsView,
    ExecutionVenueRunParityView,
    ExecutionVenueSummaryView,
)

app_name = 'execution_venue'

urlpatterns = [
    path('capabilities/', ExecutionVenueCapabilitiesView.as_view(), name='capabilities'),
    path('build-payload/<int:intent_id>/', ExecutionVenueBuildPayloadView.as_view(), name='build-payload'),
    path('dry-run/<int:intent_id>/', ExecutionVenueDryRunView.as_view(), name='dry-run'),
    path('run-parity/<int:intent_id>/', ExecutionVenueRunParityView.as_view(), name='run-parity'),
    path('parity-runs/', ExecutionVenueParityRunsView.as_view(), name='parity-runs'),
    path('summary/', ExecutionVenueSummaryView.as_view(), name='summary'),
]
