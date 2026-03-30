from django.contrib import admin

from apps.experiment_lab.models import (
    ExperimentCandidate,
    ExperimentPromotionRecommendation,
    ExperimentRun,
    StrategyProfile,
    TuningChampionChallengerComparison,
    TuningExperimentRun,
)


@admin.register(StrategyProfile)
class StrategyProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug', 'profile_type', 'market_scope', 'is_active', 'updated_at')
    list_filter = ('profile_type', 'market_scope', 'is_active')
    search_fields = ('name', 'slug', 'description')


@admin.register(ExperimentRun)
class ExperimentRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'strategy_profile', 'run_type', 'status', 'started_at', 'finished_at', 'created_at')
    list_filter = ('run_type', 'status')
    search_fields = ('summary',)


@admin.register(TuningExperimentRun)
class TuningExperimentRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'started_at', 'completed_at', 'candidate_count', 'comparison_count', 'improved_count', 'degraded_count')
    search_fields = ('id',)


@admin.register(ExperimentCandidate)
class ExperimentCandidateAdmin(admin.ModelAdmin):
    list_display = ('id', 'run', 'candidate_type', 'experiment_scope', 'readiness_status', 'created_at')
    list_filter = ('candidate_type', 'experiment_scope', 'readiness_status')
    search_fields = ('challenger_label', 'baseline_reference', 'rationale')


@admin.register(TuningChampionChallengerComparison)
class TuningChampionChallengerComparisonAdmin(admin.ModelAdmin):
    list_display = ('id', 'run', 'linked_candidate', 'comparison_status', 'sample_count', 'confidence_score', 'created_at')
    list_filter = ('comparison_status',)
    search_fields = ('baseline_label', 'challenger_label', 'rationale')


@admin.register(ExperimentPromotionRecommendation)
class ExperimentPromotionRecommendationAdmin(admin.ModelAdmin):
    list_display = ('id', 'run', 'recommendation_type', 'confidence', 'created_at')
    list_filter = ('recommendation_type',)
    search_fields = ('rationale',)
