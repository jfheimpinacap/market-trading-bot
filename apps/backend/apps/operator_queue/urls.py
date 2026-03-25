from django.urls import path

from apps.operator_queue.views import (
    OperatorQueueApproveView,
    OperatorQueueDetailView,
    OperatorQueueListView,
    OperatorQueueRebuildView,
    OperatorQueueRejectView,
    OperatorQueueSnoozeView,
    OperatorQueueSummaryView,
)

urlpatterns = [
    path('', OperatorQueueListView.as_view(), name='list'),
    path('summary/', OperatorQueueSummaryView.as_view(), name='summary'),
    path('rebuild/', OperatorQueueRebuildView.as_view(), name='rebuild'),
    path('<int:pk>/', OperatorQueueDetailView.as_view(), name='detail'),
    path('<int:pk>/approve/', OperatorQueueApproveView.as_view(), name='approve'),
    path('<int:pk>/reject/', OperatorQueueRejectView.as_view(), name='reject'),
    path('<int:pk>/snooze/', OperatorQueueSnoozeView.as_view(), name='snooze'),
]
