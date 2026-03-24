from django.urls import path

from apps.continuous_demo.views import (
    ContinuousDemoCycleDetailView,
    ContinuousDemoCycleListView,
    ContinuousDemoPauseView,
    ContinuousDemoResumeView,
    ContinuousDemoRunCycleView,
    ContinuousDemoSessionDetailView,
    ContinuousDemoSessionListView,
    ContinuousDemoStartView,
    ContinuousDemoStatusView,
    ContinuousDemoStopView,
    ContinuousDemoSummaryView,
)

urlpatterns = [
    path('start/', ContinuousDemoStartView.as_view(), name='start'),
    path('stop/', ContinuousDemoStopView.as_view(), name='stop'),
    path('pause/', ContinuousDemoPauseView.as_view(), name='pause'),
    path('resume/', ContinuousDemoResumeView.as_view(), name='resume'),
    path('run-cycle/', ContinuousDemoRunCycleView.as_view(), name='run-cycle'),
    path('status/', ContinuousDemoStatusView.as_view(), name='status'),
    path('sessions/', ContinuousDemoSessionListView.as_view(), name='session-list'),
    path('sessions/<int:pk>/', ContinuousDemoSessionDetailView.as_view(), name='session-detail'),
    path('cycles/', ContinuousDemoCycleListView.as_view(), name='cycle-list'),
    path('cycles/<int:pk>/', ContinuousDemoCycleDetailView.as_view(), name='cycle-detail'),
    path('summary/', ContinuousDemoSummaryView.as_view(), name='summary'),
]
