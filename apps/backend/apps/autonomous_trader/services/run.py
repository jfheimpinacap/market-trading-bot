from __future__ import annotations

from collections import Counter

from django.db import transaction
from django.utils import timezone

from apps.autonomous_trader.models import AutonomousTradeCycleRun
from apps.autonomous_trader.services.candidate_intake import consolidate_candidates
from apps.autonomous_trader.services.decisioning import decide_candidate
from apps.autonomous_trader.services.execution import execute_candidate
from apps.autonomous_trader.services.execution_intake import run_execution_intake
from apps.autonomous_trader.services.feedback_reuse import run_feedback_reuse_engine
from apps.autonomous_trader.services.kelly_sizing import run_sizing_bridge
from apps.autonomous_trader.services.outcomes import create_outcome
from apps.autonomous_trader.services.watch import create_watch_record


@transaction.atomic
def run_autonomous_cycle(*, actor: str = 'operator-ui', cycle_mode: str = 'FULL_AUTONOMOUS_PAPER_LOOP', limit: int = 25):
    if cycle_mode == 'FULL_AUTONOMOUS_PAPER_LOOP':
        intake_result = run_execution_intake(actor=actor, limit=limit)
        executions = [
            dispatch.linked_trade_execution
            for dispatch in intake_result['dispatches']
            if dispatch.linked_trade_execution_id
        ]
        watch_records = [create_watch_record(execution=execution) for execution in executions]
        outcomes = [create_outcome(execution=execution, watch_record=watch) for execution, watch in zip(executions, watch_records, strict=False)]
        cycle_run = intake_result['run'].linked_cycle_run
        cycle_run.considered_candidate_count = intake_result['run'].considered_readiness_count
        cycle_run.watchlist_count = intake_result['run'].watch_count
        cycle_run.approved_for_execution_count = intake_result['run'].execute_now_count + intake_result['run'].execute_reduced_count
        cycle_run.executed_paper_trade_count = intake_result['run'].dispatch_count
        cycle_run.blocked_count = intake_result['run'].blocked_count + intake_result['run'].manual_review_count
        cycle_run.closed_position_count = sum(1 for o in outcomes if o.outcome_status == 'CLOSED')
        cycle_run.postmortem_handoff_count = sum(1 for o in outcomes if o.send_to_postmortem)
        cycle_run.recommendation_summary = intake_result['run'].recommendation_summary
        cycle_run.completed_at = timezone.now()
        cycle_run.save(
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
        return {
            'run': cycle_run,
            'candidates': list(cycle_run.candidates.all()),
            'decisions': intake_result['decisions'],
            'executions': executions,
            'watch_records': watch_records,
            'outcomes': outcomes,
        }

    run = AutonomousTradeCycleRun.objects.create(cycle_mode=cycle_mode, metadata={'actor': actor})
    intake = consolidate_candidates(cycle_run=run, limit=limit)
    feedback_reuse_run = run_feedback_reuse_engine(cycle_run=run, actor=actor, limit=limit)

    decisions = [decide_candidate(candidate=candidate) for candidate in intake.candidates]
    sizing_result = run_sizing_bridge(actor=actor, cycle_run_id=run.id, limit=limit)
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
    run.metadata = {
        **(run.metadata or {}),
        'feedback_reuse_run_id': feedback_reuse_run.id,
        'sizing_run_id': sizing_result['run'].id,
    }
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
