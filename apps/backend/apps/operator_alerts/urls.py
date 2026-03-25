from django.urls import path

from apps.operator_alerts import views

urlpatterns = [
    path('', views.OperatorAlertListView.as_view(), name='list'),
    path('summary/', views.OperatorAlertSummaryView.as_view(), name='summary'),
    path('digests/', views.OperatorDigestListView.as_view(), name='digests'),
    path('digests/<int:pk>/', views.OperatorDigestDetailView.as_view(), name='digest_detail'),
    path('build-digest/', views.OperatorBuildDigestView.as_view(), name='build_digest'),
    path('rebuild/', views.OperatorRebuildAlertsView.as_view(), name='rebuild'),
    path('<int:pk>/', views.OperatorAlertDetailView.as_view(), name='detail'),
    path('<int:pk>/acknowledge/', views.OperatorAlertAcknowledgeView.as_view(), name='acknowledge'),
    path('<int:pk>/resolve/', views.OperatorAlertResolveView.as_view(), name='resolve'),
]
