from django.contrib import admin

from apps.tuning_board.models import TuningImpactHypothesis, TuningProposal, TuningProposalBundle, TuningRecommendation, TuningReviewRun

admin.site.register(TuningReviewRun)
admin.site.register(TuningProposal)
admin.site.register(TuningImpactHypothesis)
admin.site.register(TuningRecommendation)
admin.site.register(TuningProposalBundle)
