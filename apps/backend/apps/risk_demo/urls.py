from django.urls import path

from apps.risk_demo.views import AssessTradeView, TradeRiskAssessmentListView

app_name = 'risk_demo'

urlpatterns = [
    path('assess-trade/', AssessTradeView.as_view(), name='assess-trade'),
    path('assessments/', TradeRiskAssessmentListView.as_view(), name='assessment-list'),
]
