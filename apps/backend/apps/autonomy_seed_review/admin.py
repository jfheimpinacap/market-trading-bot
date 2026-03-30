from django.contrib import admin

from apps.autonomy_seed_review.models import SeedResolution, SeedReviewRecommendation, SeedReviewRun

admin.site.register(SeedResolution)
admin.site.register(SeedReviewRun)
admin.site.register(SeedReviewRecommendation)
