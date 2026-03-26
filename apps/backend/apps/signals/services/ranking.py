
def rank_opportunities(signals):
    return sorted(
        signals,
        key=lambda signal: (
            signal.opportunity_status != 'PROPOSAL_READY',
            signal.opportunity_status != 'CANDIDATE',
            signal.opportunity_status != 'WATCH',
            signal.opportunity_status != 'BLOCKED',
            -float(signal.opportunity_score),
            -signal.id,
        ),
    )
