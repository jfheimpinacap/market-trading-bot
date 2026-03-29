from django.urls import path

from apps.autonomy_package.views import (
    AutonomyPackageAcknowledgeView,
    AutonomyPackageCandidatesView,
    AutonomyPackageListView,
    AutonomyPackageRecommendationListView,
    AutonomyPackageRegisterView,
    AutonomyPackageRunReviewView,
    AutonomyPackageSummaryView,
)

app_name = 'autonomy_package'

urlpatterns = [
    path('candidates/', AutonomyPackageCandidatesView.as_view(), name='candidates'),
    path('run-review/', AutonomyPackageRunReviewView.as_view(), name='run_review'),
    path('packages/', AutonomyPackageListView.as_view(), name='packages'),
    path('recommendations/', AutonomyPackageRecommendationListView.as_view(), name='recommendations'),
    path('summary/', AutonomyPackageSummaryView.as_view(), name='summary'),
    path('register/<int:decision_id>/', AutonomyPackageRegisterView.as_view(), name='register'),
    path('acknowledge/<int:package_id>/', AutonomyPackageAcknowledgeView.as_view(), name='acknowledge'),
]
