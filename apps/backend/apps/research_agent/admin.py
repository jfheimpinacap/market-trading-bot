from django.contrib import admin

from apps.research_agent.models import (
    MarketNarrativeLink,
    NarrativeAnalysis,
    NarrativeItem,
    NarrativeSource,
    ResearchCandidate,
    ResearchScanRun,
)

admin.site.register(NarrativeSource)
admin.site.register(NarrativeItem)
admin.site.register(NarrativeAnalysis)
admin.site.register(MarketNarrativeLink)
admin.site.register(ResearchCandidate)
admin.site.register(ResearchScanRun)
