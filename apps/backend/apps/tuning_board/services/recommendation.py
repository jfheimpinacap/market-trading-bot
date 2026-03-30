from collections import Counter

from apps.tuning_board.models import TuningProposal, TuningRecommendation, TuningRecommendationType, TuningReviewRun


def build_recommendations(run: TuningReviewRun) -> list[TuningRecommendation]:
    created: list[TuningRecommendation] = []

    for proposal in run.proposals.all():
        proposal_type = proposal.proposal_type
        if proposal.proposal_status == 'WATCH':
            created.append(
                TuningRecommendation.objects.create(
                    run=run,
                    target_proposal=proposal,
                    recommendation_type=TuningRecommendationType.REQUIRE_MORE_DATA,
                    rationale='Evidence is insufficient for manual approval. Keep proposal under watch.',
                    reason_codes=proposal.reason_codes,
                    confidence=proposal.evidence_strength_score,
                    blockers=proposal.blockers,
                )
            )
            continue

        if proposal.proposal_status == 'DEFERRED':
            created.append(
                TuningRecommendation.objects.create(
                    run=run,
                    target_proposal=proposal,
                    recommendation_type=TuningRecommendationType.DEFER_TUNING_CHANGE,
                    rationale='Conflicting or weak signals suggest deferring this change.',
                    reason_codes=proposal.reason_codes,
                    confidence=proposal.evidence_strength_score,
                    blockers=proposal.blockers,
                )
            )
            continue

        recommendation_type = TuningRecommendationType.REVIEW_PREDICTION_THRESHOLD
        if proposal_type == 'calibration_bias_offset':
            recommendation_type = TuningRecommendationType.REVIEW_CALIBRATION_OFFSET
        elif proposal_type in {'risk_gate_threshold', 'liquidity_floor'}:
            recommendation_type = TuningRecommendationType.REVIEW_RISK_GATE
        elif proposal_type == 'risk_size_cap':
            recommendation_type = TuningRecommendationType.REVIEW_SIZE_CAP
        elif proposal_type == 'shortlist_threshold':
            recommendation_type = TuningRecommendationType.REVIEW_SHORTLIST_THRESHOLD

        created.append(
            TuningRecommendation.objects.create(
                run=run,
                target_proposal=proposal,
                recommendation_type=recommendation_type,
                rationale='Proposal has bounded evidence and should be manually reviewed.',
                reason_codes=proposal.reason_codes,
                confidence=proposal.evidence_strength_score,
                blockers=proposal.blockers,
            )
        )

    if run.bundles.exists():
        created.append(
            TuningRecommendation.objects.create(
                run=run,
                recommendation_type=TuningRecommendationType.GROUP_IN_BUNDLE,
                rationale='Related proposals were grouped into bundles for coordinated review.',
                reason_codes=['BUNDLE_AVAILABLE'],
                confidence=0.7,
                blockers=[],
            )
        )

    breakdown = Counter(item.recommendation_type for item in created)
    if breakdown:
        run.recommendation_summary = dict(breakdown)
        run.save(update_fields=['recommendation_summary'])

    return created
