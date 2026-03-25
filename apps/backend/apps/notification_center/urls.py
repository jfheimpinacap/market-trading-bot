from django.urls import path

from apps.notification_center import views

urlpatterns = [
    path('channels/', views.NotificationChannelListCreateView.as_view(), name='channels'),
    path('rules/', views.NotificationRuleListCreateView.as_view(), name='rules'),
    path('deliveries/', views.NotificationDeliveryListView.as_view(), name='deliveries'),
    path('deliveries/<int:pk>/', views.NotificationDeliveryDetailView.as_view(), name='delivery_detail'),
    path('send-alert/<int:alert_id>/', views.SendAlertNotificationView.as_view(), name='send_alert'),
    path('send-digest/<int:digest_id>/', views.SendDigestNotificationView.as_view(), name='send_digest'),
    path('summary/', views.NotificationSummaryView.as_view(), name='summary'),
]
