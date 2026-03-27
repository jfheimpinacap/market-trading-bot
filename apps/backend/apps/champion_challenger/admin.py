from django.contrib import admin

from apps.champion_challenger.models import ChampionChallengerRun, ShadowComparisonResult, StackProfileBinding


@admin.register(StackProfileBinding)
class StackProfileBindingAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'is_champion', 'is_active', 'prediction_profile_slug', 'execution_profile', 'created_at')
    list_filter = ('is_champion', 'is_active', 'execution_profile')
    search_fields = ('name', 'prediction_profile_slug', 'research_profile_slug', 'signal_profile_slug')


@admin.register(ChampionChallengerRun)
class ChampionChallengerRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'champion_binding', 'challenger_binding', 'recommendation_code', 'created_at')
    list_filter = ('status', 'recommendation_code')
    search_fields = ('summary',)


@admin.register(ShadowComparisonResult)
class ShadowComparisonResultAdmin(admin.ModelAdmin):
    list_display = ('id', 'run', 'decision_divergence_rate', 'created_at')
