from django.urls import path

from apps.allocation_engine.views import AllocationEvaluateView, AllocationRunDetailView, AllocationRunListView, AllocationRunView, AllocationSummaryView

urlpatterns = [
    path('evaluate/', AllocationEvaluateView.as_view(), name='evaluate'),
    path('run/', AllocationRunView.as_view(), name='run'),
    path('runs/', AllocationRunListView.as_view(), name='runs'),
    path('runs/<int:pk>/', AllocationRunDetailView.as_view(), name='run-detail'),
    path('summary/', AllocationSummaryView.as_view(), name='summary'),
]
