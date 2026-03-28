from django.urls import path

from apps.approval_center.views import (
    ApprovalApproveView,
    ApprovalDetailView,
    ApprovalEscalateView,
    ApprovalExpireView,
    ApprovalListView,
    ApprovalPendingListView,
    ApprovalRejectView,
    ApprovalSummaryView,
)

app_name = 'approval_center'

urlpatterns = [
    path('', ApprovalListView.as_view(), name='list'),
    path('pending/', ApprovalPendingListView.as_view(), name='pending'),
    path('summary/', ApprovalSummaryView.as_view(), name='summary'),
    path('<int:pk>/', ApprovalDetailView.as_view(), name='detail'),
    path('<int:pk>/approve/', ApprovalApproveView.as_view(), name='approve'),
    path('<int:pk>/reject/', ApprovalRejectView.as_view(), name='reject'),
    path('<int:pk>/expire/', ApprovalExpireView.as_view(), name='expire'),
    path('<int:pk>/escalate/', ApprovalEscalateView.as_view(), name='escalate'),
]
