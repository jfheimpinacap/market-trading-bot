from django.urls import path

from apps.risk_agent.views import (
    AutonomousExecutionReadinessListView,
    RiskAssessView,
    RiskApprovalDecisionListView,
    RiskAssessmentListView,
    RiskRuntimeCandidateListView,
    RiskRuntimeRecommendationListView,
    RiskRuntimeRunListView,
    RiskRuntimeSummaryView,
    RiskRunRuntimeReviewView,
    RiskSizeView,
    RiskSizingPlanListView,
    RiskSummaryView,
    RiskPrecedentAssistView,
    RiskWatchPlanListView,
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
    path('precedent-assist/', RiskPrecedentAssistView.as_view(), name='precedent-assist'),
    path('run-runtime-review/', RiskRunRuntimeReviewView.as_view(), name='run-runtime-review'),
    path('run-intake-review/', RiskRunRuntimeReviewView.as_view(), name='run-intake-review'),
    path('intake-runs/', RiskRuntimeRunListView.as_view(), name='intake-runs'),
    path('intake-candidates/', RiskRuntimeCandidateListView.as_view(), name='intake-candidates'),
    path('approval-reviews/', RiskApprovalDecisionListView.as_view(), name='approval-reviews'),
    path('execution-readiness/', AutonomousExecutionReadinessListView.as_view(), name='execution-readiness'),
    path('intake-recommendations/', RiskRuntimeRecommendationListView.as_view(), name='intake-recommendations'),
    path('intake-summary/', RiskRuntimeSummaryView.as_view(), name='intake-summary'),
    path('runtime-candidates/', RiskRuntimeCandidateListView.as_view(), name='runtime-candidates'),
    path('approval-decisions/', RiskApprovalDecisionListView.as_view(), name='approval-decisions'),
    path('sizing-plans/', RiskSizingPlanListView.as_view(), name='sizing-plans'),
    path('watch-plans/', RiskWatchPlanListView.as_view(), name='watch-plans'),
    path('runtime-recommendations/', RiskRuntimeRecommendationListView.as_view(), name='runtime-recommendations'),
    path('runtime-summary/', RiskRuntimeSummaryView.as_view(), name='runtime-summary'),
]
