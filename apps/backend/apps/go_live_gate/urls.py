from django.urls import path

from apps.go_live_gate.views import (
    GoLiveApprovalCreateView,
    GoLiveApprovalListView,
    GoLiveChecklistListView,
    GoLiveChecklistRunView,
    GoLiveRehearsalListView,
    GoLiveRehearsalRunView,
    GoLiveStateView,
    GoLiveSummaryView,
)

urlpatterns = [
    path('state/', GoLiveStateView.as_view(), name='state'),
    path('run-checklist/', GoLiveChecklistRunView.as_view(), name='run-checklist'),
    path('checklists/', GoLiveChecklistListView.as_view(), name='checklists'),
    path('request-approval/', GoLiveApprovalCreateView.as_view(), name='request-approval'),
    path('approvals/', GoLiveApprovalListView.as_view(), name='approvals'),
    path('run-rehearsal/', GoLiveRehearsalRunView.as_view(), name='run-rehearsal'),
    path('rehearsals/', GoLiveRehearsalListView.as_view(), name='rehearsals'),
    path('summary/', GoLiveSummaryView.as_view(), name='summary'),
]
