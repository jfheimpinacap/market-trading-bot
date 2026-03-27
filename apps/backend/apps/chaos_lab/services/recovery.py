from apps.execution_simulator.models import PaperExecutionAttempt, PaperOrder
from apps.incident_commander.models import IncidentRecord
from apps.markets.models import Market
from apps.mission_control.models import MissionControlCycle, MissionControlSession
from apps.notification_center.models import NotificationDelivery
from apps.operator_queue.models import OperatorQueueItem
from apps.paper_trading.models import PaperAccount
from apps.real_data_sync.models import ProviderSyncRun
from apps.rollout_manager.models import RolloutGuardrailEvent, StackRolloutPlan, StackRolloutRun


def cleanup_injected_state(*, run_id: int) -> dict:
    marker = {'chaos_lab': True, 'chaos_run_id': run_id}

    deleted = {
        'provider_sync_runs': ProviderSyncRun.objects.filter(details=marker).delete()[0],
        'mission_cycles': MissionControlCycle.objects.filter(details=marker).delete()[0],
        'mission_sessions': MissionControlSession.objects.filter(metadata=marker).delete()[0],
        'guardrail_events': RolloutGuardrailEvent.objects.filter(metadata=marker).delete()[0],
        'rollout_runs': StackRolloutRun.objects.filter(metadata=marker).delete()[0],
        'rollout_plans': StackRolloutPlan.objects.filter(metadata=marker).delete()[0],
        'queue_items': OperatorQueueItem.objects.filter(metadata=marker).delete()[0],
        'notifications': NotificationDelivery.objects.filter(response_metadata=marker).delete()[0],
        'execution_attempts': PaperExecutionAttempt.objects.filter(metadata=marker).delete()[0],
        'paper_orders': PaperOrder.objects.filter(metadata=marker).delete()[0],
        'markets': Market.objects.filter(metadata=marker).delete()[0],
    }

    IncidentRecord.objects.filter(metadata=marker).delete()
    PaperAccount.objects.filter(slug=f'chaos-account-{run_id}').delete()

    return deleted
