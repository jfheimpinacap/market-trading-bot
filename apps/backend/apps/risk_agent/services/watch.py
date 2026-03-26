from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from apps.operator_alerts.models import OperatorAlertSeverity, OperatorAlertSource, OperatorAlertType
from apps.operator_alerts.services import emit_alert
from apps.operator_alerts.services.alerts import AlertEmitPayload
from apps.operator_queue.models import OperatorQueueItem, OperatorQueuePriority, OperatorQueueSource, OperatorQueueStatus, OperatorQueueType
from apps.paper_trading.models import PaperPositionStatus
from apps.paper_trading.services.portfolio import get_active_account
from apps.prediction_agent.models import PredictionScore
from apps.risk_agent.models import PositionWatchEvent, PositionWatchEventType, PositionWatchRun, PositionWatchSeverity, RiskAssessmentStatus


@transaction.atomic
def run_position_watch(*, metadata: dict | None = None) -> PositionWatchRun:
    metadata = metadata or {}
    account = get_active_account()
    positions = list(
        account.positions.filter(status=PaperPositionStatus.OPEN, quantity__gt=0).select_related('market').order_by('-updated_at', '-id')
    )

    run = PositionWatchRun.objects.create(status=RiskAssessmentStatus.READY, watched_positions=len(positions), metadata=metadata)

    if not positions:
        run.status = RiskAssessmentStatus.SUCCESS
        run.summary = 'No open paper positions to watch.'
        run.save(update_fields=['status', 'summary', 'updated_at'])
        return run

    events = []
    for position in positions:
        latest = PredictionScore.objects.filter(market=position.market).order_by('-created_at', '-id').first()
        entry_probability = Decimal(str(position.metadata.get('entry_market_probability', position.average_entry_price / Decimal('100'))))
        market_probability = Decimal(str(position.market.current_market_probability or '0.5'))
        latest_probability = Decimal(str(latest.system_probability if latest else market_probability))
        prob_delta = latest_probability - entry_probability

        rationale = []
        severity = PositionWatchSeverity.INFO
        event_type = PositionWatchEventType.MONITOR

        if abs(prob_delta) >= Decimal('0.12'):
            severity = PositionWatchSeverity.WARNING
            event_type = PositionWatchEventType.REVIEW_REQUIRED
            rationale.append(f'Market probability shifted by {prob_delta:.4f} from entry context.')

        if position.unrealized_pnl <= Decimal('-120.00'):
            severity = PositionWatchSeverity.HIGH
            event_type = PositionWatchEventType.EXIT_CONSIDERATION
            rationale.append(f'Unrealized PnL deterioration: {position.unrealized_pnl}.')

        if latest and Decimal(str(latest.confidence)) < Decimal('0.40'):
            severity = PositionWatchSeverity.WARNING
            event_type = PositionWatchEventType.CAUTION
            rationale.append(f'Prediction confidence deteriorated to {latest.confidence}.')

        if not rationale:
            rationale.append('No material deterioration detected; keep monitoring.')

        event = PositionWatchEvent.objects.create(
            watch_run=run,
            paper_position=position,
            event_type=event_type,
            severity=severity,
            summary=f'{position.market.title}: {event_type}',
            rationale=' '.join(rationale),
            metadata={
                'market_id': position.market_id,
                'position_id': position.id,
                'entry_probability': str(entry_probability),
                'latest_probability': str(latest_probability),
                'probability_delta': str(prob_delta),
                'paper_demo_only': True,
            },
        )
        events.append(event)

        if severity == PositionWatchSeverity.HIGH:
            OperatorQueueItem.objects.create(
                status=OperatorQueueStatus.PENDING,
                source=OperatorQueueSource.SAFETY,
                queue_type=OperatorQueueType.SAFETY_REVIEW,
                related_market=position.market,
                priority=OperatorQueuePriority.HIGH,
                headline=f'Risk watch high severity: {position.market.title}',
                summary=event.summary,
                rationale=event.rationale,
                metadata={'risk_watch_event_id': event.id, 'paper_demo_only': True},
            )
            emit_alert(
                AlertEmitPayload(
                    alert_type=OperatorAlertType.PORTFOLIO,
                    severity=OperatorAlertSeverity.HIGH,
                    title=f'Risk watch high severity for {position.market.title}',
                    summary=event.rationale,
                    source=OperatorAlertSource.MANUAL,
                    dedupe_key=f'risk-watch:{position.id}:{event.event_type}',
                    related_object_type='position_watch_event',
                    related_object_id=str(event.id),
                    metadata={'paper_demo_only': True},
                )
            )

    run.status = RiskAssessmentStatus.SUCCESS
    run.generated_events = len(events)
    run.summary = f'Watched {len(positions)} open positions and produced {len(events)} events.'
    run.save(update_fields=['status', 'generated_events', 'summary', 'updated_at'])
    return run
