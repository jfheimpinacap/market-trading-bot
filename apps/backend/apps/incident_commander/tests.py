from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.incident_commander.models import DegradedModeState, IncidentRecord
from apps.incident_commander.services import mitigate_incident, resolve_incident, run_detection
from apps.memory_retrieval.models import MemoryDocument
from apps.mission_control.models import MissionControlCycle, MissionControlSession
from apps.operator_queue.models import OperatorQueueItem, OperatorQueueStatus
from apps.real_data_sync.models import ProviderSyncRun
from apps.champion_challenger.models import StackProfileBinding
from apps.rollout_manager.models import RolloutGuardrailEvent, StackRolloutPlan, StackRolloutRun


class IncidentCommanderTests(TestCase):
    def test_detection_creates_and_dedupes_incident(self):
        ProviderSyncRun.objects.create(
            provider='kalshi',
            sync_type='full',
            status='FAILED',
            started_at=timezone.now() - timedelta(hours=3),
            errors_count=3,
        )

        first = run_detection()
        second = run_detection()

        self.assertGreaterEqual(first['detected_count'], 1)
        self.assertGreaterEqual(second['detected_count'], 1)
        self.assertEqual(IncidentRecord.objects.filter(incident_type='stale_data').count(), 1)

    def test_degraded_mode_activation_and_resolution(self):
        incident = IncidentRecord.objects.create(
            incident_type='queue_pressure',
            severity='high',
            status='OPEN',
            title='Queue pressure test',
            summary='Queue pressure high',
            source_app='operator_queue',
            first_seen_at=timezone.now(),
            last_seen_at=timezone.now(),
            dedupe_key='test-queue-pressure',
        )

        mitigate_incident(incident=incident)
        incident.refresh_from_db()
        self.assertIn(incident.status, {'DEGRADED', 'MITIGATING'})

        state = DegradedModeState.objects.order_by('-updated_at').first()
        self.assertIsNotNone(state)
        self.assertFalse(state.auto_execution_enabled)

        resolve_incident(incident=incident, resolution_note='Recovered in test')
        incident.refresh_from_db()
        self.assertEqual(incident.status, 'RESOLVED')

    def test_mission_control_and_rollout_detection_paths(self):
        session = MissionControlSession.objects.create(status='RUNNING', summary='test', metadata={'slug': 'balanced_mission_control'})
        for index in range(4):
            MissionControlCycle.objects.create(
                session=session,
                cycle_number=index + 1,
                status='FAILED',
                started_at=timezone.now() - timedelta(minutes=index + 1),
            )

        champion = StackProfileBinding.objects.create(name='champion', is_champion=True, execution_profile='balanced_paper')
        candidate = StackProfileBinding.objects.create(name='candidate', is_champion=False, execution_profile='balanced_paper')
        plan = StackRolloutPlan.objects.create(
            champion_binding=champion,
            candidate_binding=candidate,
            mode='CANARY',
            canary_percentage=10,
            guardrails={},
        )
        run = StackRolloutRun.objects.create(plan=plan, status='RUNNING')
        RolloutGuardrailEvent.objects.create(run=run, code='EXECUTION_DRAG_SPIKE', severity='CRITICAL', reason='critical test event')

        result = run_detection()
        self.assertGreaterEqual(result['detected_count'], 2)

    def test_api_endpoints(self):
        incident = IncidentRecord.objects.create(
            incident_type='memory_index_failure',
            severity='warning',
            status='OPEN',
            title='Memory indexing delayed',
            summary='Missing embeddings',
            source_app='memory_retrieval',
            first_seen_at=timezone.now(),
            last_seen_at=timezone.now(),
            dedupe_key='memory-issue',
        )
        doc = MemoryDocument.objects.create(
            document_type='learning_note',
            source_app='learning_memory',
            source_object_id='1',
            title='memory',
            text_content='test',
            embedded_at=None,
        )
        doc.created_at = timezone.now() - timedelta(hours=8)
        doc.save(update_fields=['created_at', 'updated_at'])
        for index in range(22):
            OperatorQueueItem.objects.create(status=OperatorQueueStatus.PENDING, source='semi_auto', queue_type='blocked_review', headline=f'x{index}', summary='x', rationale='x')

        list_res = self.client.get(reverse('incident_commander:list'))
        state_res = self.client.get(reverse('incident_commander:current_state'))
        detection_res = self.client.post(reverse('incident_commander:run_detection'), data='{}', content_type='application/json')
        mitigate_res = self.client.post(reverse('incident_commander:mitigate', args=[incident.id]), data='{}', content_type='application/json')
        resolve_res = self.client.post(reverse('incident_commander:resolve', args=[incident.id]), data='{}', content_type='application/json')
        summary_res = self.client.get(reverse('incident_commander:summary'))

        self.assertEqual(list_res.status_code, 200)
        self.assertEqual(state_res.status_code, 200)
        self.assertEqual(detection_res.status_code, 200)
        self.assertEqual(mitigate_res.status_code, 200)
        self.assertEqual(resolve_res.status_code, 200)
        self.assertEqual(summary_res.status_code, 200)
