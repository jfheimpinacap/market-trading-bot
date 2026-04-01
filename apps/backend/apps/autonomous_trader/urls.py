from django.urls import path

from apps.autonomous_trader.views import (
    AutonomousLearningHandoffsView,
    AutonomousOutcomeHandoffRecommendationsView,
    AutonomousOutcomeHandoffRunsView,
    AutonomousOutcomeHandoffSummaryView,
    AutonomousPostmortemHandoffsView,
    AutonomousTradeCandidatesView,
    AutonomousTradeCycleDetailView,
    AutonomousTradeCyclesView,
    AutonomousTradeDecisionsView,
    AutonomousTradeExecutionsView,
    AutonomousTradeOutcomesView,
    AutonomousTradeRunCycleView,
    AutonomousTradeRunOutcomeHandoffView,
    AutonomousTradeRunWatchCycleView,
    AutonomousTradeSummaryView,
    AutonomousTradeWatchRecordsView,
)

app_name = 'autonomous_trader'

urlpatterns = [
    path('run-cycle/', AutonomousTradeRunCycleView.as_view(), name='run-cycle'),
    path('run-watch-cycle/', AutonomousTradeRunWatchCycleView.as_view(), name='run-watch-cycle'),
    path('run-outcome-handoff/', AutonomousTradeRunOutcomeHandoffView.as_view(), name='run-outcome-handoff'),
    path('cycles/', AutonomousTradeCyclesView.as_view(), name='cycles'),
    path('cycles/<int:cycle_id>/', AutonomousTradeCycleDetailView.as_view(), name='cycle-detail'),
    path('candidates/', AutonomousTradeCandidatesView.as_view(), name='candidates'),
    path('decisions/', AutonomousTradeDecisionsView.as_view(), name='decisions'),
    path('executions/', AutonomousTradeExecutionsView.as_view(), name='executions'),
    path('watch-records/', AutonomousTradeWatchRecordsView.as_view(), name='watch-records'),
    path('outcomes/', AutonomousTradeOutcomesView.as_view(), name='outcomes'),
    path('summary/', AutonomousTradeSummaryView.as_view(), name='summary'),
    path('outcome-handoff-runs/', AutonomousOutcomeHandoffRunsView.as_view(), name='outcome-handoff-runs'),
    path('postmortem-handoffs/', AutonomousPostmortemHandoffsView.as_view(), name='postmortem-handoffs'),
    path('learning-handoffs/', AutonomousLearningHandoffsView.as_view(), name='learning-handoffs'),
    path('outcome-handoff-recommendations/', AutonomousOutcomeHandoffRecommendationsView.as_view(), name='outcome-handoff-recommendations'),
    path('outcome-handoff-summary/', AutonomousOutcomeHandoffSummaryView.as_view(), name='outcome-handoff-summary'),
]
