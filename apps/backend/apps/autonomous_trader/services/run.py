from __future__ import annotations

from collections import Counter

from django.db import transaction
from django.utils import timezone

from apps.autonomous_trader.models import AutonomousTradeCycleRun
from apps.autonomous_trader.services.candidate_intake import consolidate_candidates
from apps.autonomous_trader.services.decisioning import decide_candidate
from apps.autonomous_trader.services.execution import execute_candidate
from apps.autonomous_trader.services.outcomes import create_outcome
from apps.autonomous_trader.services.watch import create_watch_record


@transaction.atomic
def run_autonomous_cycle(*, actor: str = 'operator-ui', cycle_mode: str = 'FULL_AUTONOMOUS_PAPER_LOOP', limit: int = 25):
    run = AutonomousTradeCycleRun.objects.create(cycle_mode=cycle_mode, metadata={'actor': actor})
    intake = consolidate_candidates(cycle_run=run, limit=limit)

    decisions = [decide_candidate(candidate=candidate) for candidate in intake.candidates]
    executions = [execute_candidate(decision=decision) for decision in decisions]
    watch_records = [create_watch_record(execution=execution) for execution in executions]
    outcomes = [create_outcome(execution=execution, watch_record=watch) for execution, watch in zip(executions, watch_records, strict=False)]

    decision_counter = Counter(d.decision_type for d in decisions)
    run.considered_candidate_count = len(intake.candidates)
    run.watchlist_count = decision_counter.get('KEEP_ON_WATCH', 0)
    run.approved_for_execution_count = decision_counter.get('EXECUTE_PAPER_TRADE', 0)
    run.executed_paper_trade_count = sum(1 for e in executions if e.execution_status == 'FILLED')
    run.blocked_count = sum(1 for d in decisions if d.decision_status == 'BLOCKED')
    run.closed_position_count = sum(1 for o in outcomes if o.outcome_status == 'CLOSED')
    run.postmortem_handoff_count = sum(1 for o in outcomes if o.send_to_postmortem)
    run.recommendation_summary = dict(decision_counter)
    run.completed_at = timezone.now()
    run.save(
        update_fields=[
            'considered_candidate_count',
            'watchlist_count',
            'approved_for_execution_count',
            'executed_paper_trade_count',
            'blocked_count',
            'closed_position_count',
            'postmortem_handoff_count',
            'recommendation_summary',
            'completed_at',
            'updated_at',
        ]
    )

    return {'run': run, 'candidates': intake.candidates, 'decisions': decisions, 'executions': executions, 'watch_records': watch_records, 'outcomes': outcomes}


def build_summary() -> dict:
    latest = AutonomousTradeCycleRun.objects.order_by('-started_at', '-id').first()
    if not latest:
        return {
            'latest_run_id': None,
            'considered_candidate_count': 0,
            'watchlist_count': 0,
            'approved_for_execution_count': 0,
            'executed_paper_trade_count': 0,
            'blocked_count': 0,
            'closed_position_count': 0,
            'postmortem_handoff_count': 0,
            'recommendation_summary': {},
        }

    return {
        'latest_run_id': latest.id,
        'considered_candidate_count': latest.considered_candidate_count,
        'watchlist_count': latest.watchlist_count,
        'approved_for_execution_count': latest.approved_for_execution_count,
        'executed_paper_trade_count': latest.executed_paper_trade_count,
        'blocked_count': latest.blocked_count,
        'closed_position_count': latest.closed_position_count,
        'postmortem_handoff_count': latest.postmortem_handoff_count,
        'recommendation_summary': latest.recommendation_summary,
    }
