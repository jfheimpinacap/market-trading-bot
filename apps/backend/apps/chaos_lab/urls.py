from django.urls import path

from apps.chaos_lab import views

urlpatterns = [
    path('experiments/', views.ChaosExperimentListView.as_view(), name='experiments'),
    path('run/', views.ChaosRunCreateView.as_view(), name='run'),
    path('runs/', views.ChaosRunListView.as_view(), name='runs'),
    path('runs/<int:pk>/', views.ChaosRunDetailView.as_view(), name='run-detail'),
    path('benchmarks/', views.ChaosBenchmarkListView.as_view(), name='benchmarks'),
    path('summary/', views.ChaosSummaryView.as_view(), name='summary'),
]
