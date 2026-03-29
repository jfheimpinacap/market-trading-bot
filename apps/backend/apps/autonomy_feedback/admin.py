from django.contrib import admin

from apps.autonomy_feedback.models import FeedbackRecommendation, FeedbackRun, FollowupResolution


admin.site.register(FollowupResolution)
admin.site.register(FeedbackRun)
admin.site.register(FeedbackRecommendation)
