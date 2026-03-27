from django.urls import path

from apps.execution_simulator import views

app_name = 'execution_simulator'

urlpatterns = [
    path('create-order/', views.ExecutionCreateOrderView.as_view(), name='create-order'),
    path('run-lifecycle/', views.ExecutionRunLifecycleView.as_view(), name='run-lifecycle'),
    path('orders/', views.ExecutionOrdersView.as_view(), name='orders'),
    path('orders/<int:pk>/', views.ExecutionOrderDetailView.as_view(), name='order-detail'),
    path('fills/', views.ExecutionFillsView.as_view(), name='fills'),
    path('summary/', views.ExecutionSummaryView.as_view(), name='summary'),
]
