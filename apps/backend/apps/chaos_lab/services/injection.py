from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from apps.champion_challenger.models import StackProfileBinding
from apps.champion_challenger.services.bindings import get_or_create_champion_binding
from apps.execution_simulator.models import PaperExecutionAttempt, PaperOrder
from apps.incident_commander.models import IncidentRecord
from apps.markets.models import Market, MarketSourceType, MarketStatus, Provider
from apps.mission_control.models import MissionControlCycle, MissionControlSession
from apps.notification_center.models import NotificationDelivery
from apps.operator_queue.models import OperatorQueueItem
from apps.paper_trading.models import PaperAccount
from apps.real_data_sync.models import ProviderSyncRun
from apps.rollout_manager.models import RolloutGuardrailEvent, StackRolloutPlan, StackRolloutRun


@dataclass
class InjectionResult:
    injections: list[dict]


def _marker(run_id: int) -> dict:
    return {'chaos_lab': True, 'chaos_run_id': run_id}


def apply_injection(*, experiment, run) -> InjectionResult:
    now = timezone.now()
    marker = _marker(run.id)
    injections: list[dict] = []

    if experiment.experiment_type in {'provider_sync_failure', 'stale_data_scenario'}:
        stale_hours = int((experiment.config or {}).get('stale_hours', 3))
        sync = ProviderSyncRun.objects.create(
            provider=(experiment.config or {}).get('provider', 'kalshi'),
            sync_type='full',
            status='FAILED',
            started_at=now - timedelta(hours=stale_hours),
            finished_at=now - timedelta(hours=max(stale_hours - 1, 0)),
            triggered_from='chaos_lab',
            errors_count=3,
            summary='Chaos injected provider sync failure',
            details=marker,
        )
        injections.append({'type': 'provider_sync_failure', 'target': 'real_data_sync.ProviderSyncRun', 'object_id': sync.id, 'duration_hint_seconds': 0, 'parameters': {'stale_hours': stale_hours}})

    elif experiment.experiment_type == 'mission_control_step_failure':
        failed_cycles = int((experiment.config or {}).get('failed_cycles', 4))
        session = MissionControlSession.objects.create(status='RUNNING', summary='Chaos mission control failure session', metadata=marker)
        created_ids = []
        for index in range(failed_cycles):
            cycle = MissionControlCycle.objects.create(
                session=session,
                cycle_number=index + 1,
                status='FAILED',
                started_at=now - timedelta(minutes=index + 1),
                finished_at=now - timedelta(minutes=index + 1),
                summary='Chaos injected failed cycle',
                details=marker,
            )
            created_ids.append(cycle.id)
        injections.append({'type': 'mission_control_step_failure', 'target': 'mission_control.MissionControlCycle', 'object_id': session.id, 'duration_hint_seconds': 0, 'parameters': {'failed_cycle_ids': created_ids}})

    elif experiment.experiment_type == 'rollout_guardrail_trigger':
        champion = get_or_create_champion_binding()
        candidate = StackProfileBinding.objects.create(name=f'chaos_candidate_{run.id}', is_champion=False, execution_profile='balanced_paper')
        plan = StackRolloutPlan.objects.create(champion_binding=champion, candidate_binding=candidate, mode='CANARY', canary_percentage=20, metadata=marker)
        rollout_run = StackRolloutRun.objects.create(plan=plan, status='RUNNING', metadata=marker)
        event = RolloutGuardrailEvent.objects.create(
            run=rollout_run,
            code=(experiment.config or {}).get('guardrail_code', 'EXECUTION_DRAG_SPIKE'),
            severity='CRITICAL',
            reason='Chaos injected critical guardrail event',
            metadata=marker,
        )
        injections.append({'type': 'rollout_guardrail_trigger', 'target': 'rollout_manager.RolloutGuardrailEvent', 'object_id': event.id, 'duration_hint_seconds': 0, 'parameters': {'run_id': rollout_run.id}})

    elif experiment.experiment_type == 'queue_pressure_spike':
        pending_items = int((experiment.config or {}).get('pending_items', 22))
        item_ids = []
        for index in range(pending_items):
            item = OperatorQueueItem.objects.create(
                status='PENDING',
                source='semi_auto',
                queue_type='blocked_review',
                priority='high',
                headline=f'Chaos queue pressure #{index + 1}',
                summary='Injected backlog pressure for resilience validation.',
                rationale='chaos_lab injection',
                metadata=marker,
            )
            item_ids.append(item.id)
        injections.append({'type': 'queue_pressure_spike', 'target': 'operator_queue.OperatorQueueItem', 'object_id': item_ids[0] if item_ids else None, 'duration_hint_seconds': 0, 'parameters': {'created_items': len(item_ids)}})

    elif experiment.experiment_type == 'notification_delivery_failure':
        count = int((experiment.config or {}).get('failed_deliveries', 6))
        created = []
        for index in range(count):
            delivery = NotificationDelivery.objects.create(
                delivery_status='FAILED',
                delivery_mode='immediate',
                trigger_source='automatic',
                reason='Chaos injected failed delivery',
                payload_preview={'index': index, **marker},
                response_metadata=marker,
                fingerprint=f'chaos-lab:{run.id}:{index}',
            )
            created.append(delivery.id)
        injections.append({'type': 'notification_delivery_failure', 'target': 'notification_center.NotificationDelivery', 'object_id': created[0] if created else None, 'duration_hint_seconds': 0, 'parameters': {'created_deliveries': len(created)}})

    elif experiment.experiment_type == 'execution_fill_anomaly':
        failed_attempts = int((experiment.config or {}).get('failed_attempts', 13))
        provider, _ = Provider.objects.get_or_create(slug='kalshi', defaults={'name': 'Kalshi'})
        market = Market.objects.create(
            provider=provider,
            title=f'Chaos execution market #{run.id}',
            slug=f'chaos-execution-market-{run.id}',
            source_type=MarketSourceType.DEMO,
            is_active=True,
            status=MarketStatus.OPEN,
            current_yes_price=Decimal('54'),
            current_no_price=Decimal('46'),
            metadata=marker,
        )
        account = PaperAccount.objects.create(name=f'Chaos account {run.id}', slug=f'chaos-account-{run.id}')
        order = PaperOrder.objects.create(
            paper_account=account,
            market=market,
            side='BUY_YES',
            requested_quantity=Decimal('10'),
            remaining_quantity=Decimal('10'),
            order_type='market_like',
            status='OPEN',
            metadata=marker,
        )
        ids = []
        for _ in range(failed_attempts):
            attempt = PaperExecutionAttempt.objects.create(
                paper_order=order,
                attempt_status='NO_FILL',
                rationale='Chaos injected no-fill anomaly',
                metadata=marker,
            )
            ids.append(attempt.id)
        injections.append({'type': 'execution_fill_anomaly', 'target': 'execution_simulator.PaperExecutionAttempt', 'object_id': ids[0] if ids else None, 'duration_hint_seconds': 0, 'parameters': {'attempts': len(ids), 'order_id': order.id}})

    elif experiment.experiment_type == 'llm_unavailable':
        incident = IncidentRecord.objects.create(
            incident_type='llm_unavailable',
            severity='warning',
            status='OPEN',
            title='Chaos synthetic local LLM unavailable',
            summary='Synthetic incident to validate mitigation/recovery path where LLM health probes are unavailable in test mode.',
            source_app='llm_local',
            first_seen_at=now,
            last_seen_at=now,
            dedupe_key=f'chaos-llm:{run.id}',
            metadata=marker,
        )
        injections.append({'type': 'llm_unavailable', 'target': 'incident_commander.IncidentRecord', 'object_id': incident.id, 'duration_hint_seconds': 0, 'parameters': {'synthetic': True}})

    else:
        injections.append({'type': experiment.experiment_type, 'target': experiment.target_module, 'object_id': None, 'duration_hint_seconds': 0, 'parameters': {'note': 'No-op injection for unsupported type.'}})

    return InjectionResult(injections=injections)
