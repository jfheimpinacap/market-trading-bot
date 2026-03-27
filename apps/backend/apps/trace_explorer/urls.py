from django.urls import path

from apps.trace_explorer.views import (
    TraceQueryRunListView,
    TraceQueryView,
    TraceRootDetailView,
    TraceRootListView,
    TraceSnapshotView,
    TraceSummaryView,
)

app_name = 'trace_explorer'

urlpatterns = [
    path('query/', TraceQueryView.as_view(), name='query'),
    path('roots/', TraceRootListView.as_view(), name='roots'),
    path('roots/<int:pk>/', TraceRootDetailView.as_view(), name='root-detail'),
    path('snapshot/<str:root_type>/<str:root_id>/', TraceSnapshotView.as_view(), name='snapshot'),
    path('query-runs/', TraceQueryRunListView.as_view(), name='query-runs'),
    path('summary/', TraceSummaryView.as_view(), name='summary'),
]
