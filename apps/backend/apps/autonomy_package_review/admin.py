from django.contrib import admin

from apps.autonomy_package_review.models import PackageResolution, PackageReviewRecommendation, PackageReviewRun

admin.site.register(PackageResolution)
admin.site.register(PackageReviewRun)
admin.site.register(PackageReviewRecommendation)
