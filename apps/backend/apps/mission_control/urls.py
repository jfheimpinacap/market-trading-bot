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
]
