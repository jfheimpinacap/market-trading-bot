from django.contrib import admin

from apps.autonomy_package.models import GovernancePackage, PackageRecommendation, PackageRun

admin.site.register(GovernancePackage)
admin.site.register(PackageRun)
admin.site.register(PackageRecommendation)
