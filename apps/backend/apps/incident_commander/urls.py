from django.urls import path

from apps.incident_commander import views

urlpatterns = [
    path('', views.IncidentListView.as_view(), name='list'),
    path('summary/', views.IncidentSummaryView.as_view(), name='summary'),
    path('current-state/', views.IncidentCurrentStateView.as_view(), name='current_state'),
    path('run-detection/', views.IncidentRunDetectionView.as_view(), name='run_detection'),
    path('<int:pk>/', views.IncidentDetailView.as_view(), name='detail'),
    path('<int:pk>/mitigate/', views.IncidentMitigateView.as_view(), name='mitigate'),
    path('<int:pk>/resolve/', views.IncidentResolveView.as_view(), name='resolve'),
]
