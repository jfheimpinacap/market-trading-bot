from django.contrib import admin

from apps.autonomy_seed.models import GovernanceSeed, SeedRecommendation, SeedRun


@admin.register(GovernanceSeed)
class GovernanceSeedAdmin(admin.ModelAdmin):
    list_display = ('id', 'governance_package', 'seed_type', 'seed_status', 'target_scope', 'priority_level', 'registered_at')
    list_filter = ('seed_type', 'seed_status', 'target_scope', 'priority_level')
    search_fields = ('title', 'summary', 'grouping_key')


@admin.register(SeedRun)
class SeedRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'candidate_count', 'ready_count', 'blocked_count', 'registered_count', 'duplicate_skipped_count', 'created_at')
    ordering = ('-created_at',)


@admin.register(SeedRecommendation)
class SeedRecommendationAdmin(admin.ModelAdmin):
    list_display = ('id', 'recommendation_type', 'seed_type', 'governance_package', 'created_at')
    list_filter = ('recommendation_type', 'seed_type')
    ordering = ('-created_at',)
