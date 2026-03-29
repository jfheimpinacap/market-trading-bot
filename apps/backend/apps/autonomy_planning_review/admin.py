from django.contrib import admin

from apps.autonomy_planning_review.models import PlanningProposalResolution, PlanningReviewRecommendation, PlanningReviewRun

admin.site.register(PlanningProposalResolution)
admin.site.register(PlanningReviewRun)
admin.site.register(PlanningReviewRecommendation)
