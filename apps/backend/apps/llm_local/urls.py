from django.urls import path

from apps.llm_local.views import LearningNoteView, LlmEmbedView, LlmStatusView, PostmortemSummaryView, ProposalThesisView

app_name = 'llm_local'

urlpatterns = [
    path('status/', LlmStatusView.as_view(), name='status'),
    path('proposal-thesis/', ProposalThesisView.as_view(), name='proposal-thesis'),
    path('postmortem-summary/', PostmortemSummaryView.as_view(), name='postmortem-summary'),
    path('learning-note/', LearningNoteView.as_view(), name='learning-note'),
    path('embed/', LlmEmbedView.as_view(), name='embed'),
]
