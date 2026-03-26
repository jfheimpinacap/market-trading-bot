from django.urls import path

from apps.risk_agent.views import (
    RiskAssessView,
    RiskAssessmentListView,
    RiskSizeView,
    RiskSummaryView,
    RiskWatchEventListView,
    RiskWatchRunView,
)

app_name = 'risk_agent'

urlpatterns = [
    path('assess/', RiskAssessView.as_view(), name='assess'),
    path('size/', RiskSizeView.as_view(), name='size'),
    path('run-watch/', RiskWatchRunView.as_view(), name='run-watch'),
    path('assessments/', RiskAssessmentListView.as_view(), name='assessments'),
    path('watch-events/', RiskWatchEventListView.as_view(), name='watch-events'),
    path('summary/', RiskSummaryView.as_view(), name='summary'),
]
