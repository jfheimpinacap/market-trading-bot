from collections import defaultdict

from apps.tuning_board.models import TuningBundleStatus, TuningProposal, TuningProposalBundle, TuningProposalStatus, TuningReviewRun


def build_bundles(run: TuningReviewRun) -> list[TuningProposalBundle]:
    groups: dict[str, list[TuningProposal]] = defaultdict(list)
    for proposal in run.proposals.all():
        key = f"{proposal.target_scope}:{proposal.target_value or 'global'}"
        groups[key].append(proposal)

    bundles: list[TuningProposalBundle] = []
    for key, proposals in groups.items():
        if len(proposals) < 2:
            continue
        if any(item.proposal_status == TuningProposalStatus.WATCH for item in proposals):
            status = TuningBundleStatus.NEEDS_MORE_DATA
        elif any(item.proposal_status == TuningProposalStatus.READY_FOR_REVIEW for item in proposals):
            status = TuningBundleStatus.READY_FOR_REVIEW
        else:
            status = TuningBundleStatus.PROPOSED

        bundle = TuningProposalBundle.objects.create(
            run=run,
            bundle_label=f'{key} tuning cluster',
            bundle_scope=key,
            bundle_status=status,
            rationale='Related proposals grouped to preserve coordinated manual review.',
            metadata={'proposal_ids': [item.id for item in proposals]},
        )
        bundle.linked_proposals.set(proposals)
        bundles.append(bundle)
    return bundles
