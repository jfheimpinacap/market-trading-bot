from django.urls import path

from apps.semi_auto_demo.views import (
    PendingApprovalApproveView,
    PendingApprovalListView,
    PendingApprovalRejectView,
    SemiAutoEvaluateView,
    SemiAutoRunDetailView,
    SemiAutoRunListView,
    SemiAutoRunView,
    SemiAutoSummaryView,
)

app_name = 'semi_auto_demo'

urlpatterns = [
    path('evaluate/', SemiAutoEvaluateView.as_view(), name='evaluate'),
    path('run/', SemiAutoRunView.as_view(), name='run'),
    path('runs/', SemiAutoRunListView.as_view(), name='run-list'),
    path('runs/<int:pk>/', SemiAutoRunDetailView.as_view(), name='run-detail'),
    path('pending-approvals/', PendingApprovalListView.as_view(), name='pending-approval-list'),
    path('pending-approvals/<int:pk>/approve/', PendingApprovalApproveView.as_view(), name='pending-approval-approve'),
    path('pending-approvals/<int:pk>/reject/', PendingApprovalRejectView.as_view(), name='pending-approval-reject'),
    path('summary/', SemiAutoSummaryView.as_view(), name='summary'),
]
