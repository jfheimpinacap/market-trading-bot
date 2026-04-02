from django.urls import path

from apps.mission_control import views

app_name = 'mission_control'

urlpatterns = [
    path('status/', views.MissionControlStatusView.as_view(), name='status'),
    path('start/', views.MissionControlStartView.as_view(), name='start'),
    path('pause/', views.MissionControlPauseView.as_view(), name='pause'),
    path('resume/', views.MissionControlResumeView.as_view(), name='resume'),
    path('stop/', views.MissionControlStopView.as_view(), name='stop'),
    path('run-cycle/', views.MissionControlRunCycleView.as_view(), name='run-cycle'),
    path('sessions/', views.MissionControlSessionListView.as_view(), name='session-list'),
    path('sessions/<int:pk>/', views.MissionControlSessionDetailView.as_view(), name='session-detail'),
    path('cycles/', views.MissionControlCycleListView.as_view(), name='cycle-list'),
    path('cycles/<int:pk>/', views.MissionControlCycleDetailView.as_view(), name='cycle-detail'),
    path('summary/', views.MissionControlSummaryView.as_view(), name='summary'),
    path('run-autonomous-runtime/', views.RunAutonomousRuntimeView.as_view(), name='run-autonomous-runtime'),
    path('autonomous-runtime-runs/', views.AutonomousRuntimeRunListView.as_view(), name='autonomous-runtime-runs'),
    path('autonomous-cycle-plans/', views.AutonomousCyclePlanListView.as_view(), name='autonomous-cycle-plans'),
    path('autonomous-cycle-executions/', views.AutonomousCycleExecutionListView.as_view(), name='autonomous-cycle-executions'),
    path('autonomous-cycle-outcomes/', views.AutonomousCycleOutcomeListView.as_view(), name='autonomous-cycle-outcomes'),
    path('autonomous-runtime-recommendations/', views.AutonomousRuntimeRecommendationListView.as_view(), name='autonomous-runtime-recommendations'),
    path('autonomous-runtime-summary/', views.AutonomousRuntimeSummaryView.as_view(), name='autonomous-runtime-summary'),
    path('start-autonomous-session/', views.StartAutonomousSessionView.as_view(), name='start-autonomous-session'),
    path('pause-autonomous-session/<int:session_id>/', views.PauseAutonomousSessionView.as_view(), name='pause-autonomous-session'),
    path('resume-autonomous-session/<int:session_id>/', views.ResumeAutonomousSessionView.as_view(), name='resume-autonomous-session'),
    path('stop-autonomous-session/<int:session_id>/', views.StopAutonomousSessionView.as_view(), name='stop-autonomous-session'),
    path('run-autonomous-tick/<int:session_id>/', views.RunAutonomousTickView.as_view(), name='run-autonomous-tick'),
    path('autonomous-sessions/', views.AutonomousSessionListView.as_view(), name='autonomous-sessions'),
    path('autonomous-sessions/<int:pk>/', views.AutonomousSessionDetailView.as_view(), name='autonomous-session-detail'),
    path('autonomous-ticks/', views.AutonomousTickListView.as_view(), name='autonomous-ticks'),
    path('autonomous-ticks/<int:pk>/', views.AutonomousTickDetailView.as_view(), name='autonomous-tick-detail'),
    path('autonomous-cadence-decisions/', views.AutonomousCadenceDecisionListView.as_view(), name='autonomous-cadence-decisions'),
    path('autonomous-session-recommendations/', views.AutonomousSessionRecommendationListView.as_view(), name='autonomous-session-recommendations'),
    path('autonomous-session-summary/', views.AutonomousSessionSummaryView.as_view(), name='autonomous-session-summary'),
]
