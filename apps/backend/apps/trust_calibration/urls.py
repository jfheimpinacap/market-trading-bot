from django.urls import path

from apps.trust_calibration.views import (
    TrustCalibrationFeedbackListView,
    TrustCalibrationRecommendationListView,
    TrustCalibrationRunCreateView,
    TrustCalibrationRunDetailView,
    TrustCalibrationRunListView,
    TrustCalibrationRunReportView,
    TrustCalibrationSummaryView,
)

app_name = 'trust_calibration'

urlpatterns = [
    path('run/', TrustCalibrationRunCreateView.as_view(), name='run'),
    path('runs/', TrustCalibrationRunListView.as_view(), name='runs'),
    path('runs/<int:pk>/', TrustCalibrationRunDetailView.as_view(), name='run-detail'),
    path('runs/<int:pk>/report/', TrustCalibrationRunReportView.as_view(), name='run-report'),
    path('recommendations/', TrustCalibrationRecommendationListView.as_view(), name='recommendations'),
    path('summary/', TrustCalibrationSummaryView.as_view(), name='summary'),
    path('feedback/', TrustCalibrationFeedbackListView.as_view(), name='feedback'),
]
