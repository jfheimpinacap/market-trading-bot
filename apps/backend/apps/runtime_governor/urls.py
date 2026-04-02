from django.urls import path

from apps.runtime_governor.views import (
    ApplyOperatingModeDecisionView,
    OperatingModeDecisionDetailView,
    OperatingModeDecisionListView,
    OperatingModeRecommendationListView,
    OperatingModeSummaryView,
    OperatingModeSwitchRecordListView,
    RunOperatingModeReviewView,
    RuntimeCapabilitiesView,
    RuntimeModesView,
    RuntimePostureRunListView,
    RuntimePostureSnapshotListView,
    RuntimeSetModeView,
    RuntimeStatusView,
    RuntimeTransitionListView,
)

urlpatterns = [
    path('status/', RuntimeStatusView.as_view(), name='status'),
    path('modes/', RuntimeModesView.as_view(), name='modes'),
    path('set-mode/', RuntimeSetModeView.as_view(), name='set_mode'),
    path('transitions/', RuntimeTransitionListView.as_view(), name='transitions'),
    path('capabilities/', RuntimeCapabilitiesView.as_view(), name='capabilities'),
    path('run-operating-mode-review/', RunOperatingModeReviewView.as_view(), name='run_operating_mode_review'),
    path('runtime-posture-runs/', RuntimePostureRunListView.as_view(), name='runtime_posture_runs'),
    path('runtime-posture-snapshots/', RuntimePostureSnapshotListView.as_view(), name='runtime_posture_snapshots'),
    path('operating-mode-decisions/', OperatingModeDecisionListView.as_view(), name='operating_mode_decisions'),
    path('operating-mode-decisions/<int:decision_id>/', OperatingModeDecisionDetailView.as_view(), name='operating_mode_decision_detail'),
    path('operating-mode-switch-records/', OperatingModeSwitchRecordListView.as_view(), name='operating_mode_switch_records'),
    path('operating-mode-recommendations/', OperatingModeRecommendationListView.as_view(), name='operating_mode_recommendations'),
    path('operating-mode-summary/', OperatingModeSummaryView.as_view(), name='operating_mode_summary'),
    path('apply-operating-mode/<int:decision_id>/', ApplyOperatingModeDecisionView.as_view(), name='apply_operating_mode'),
]
