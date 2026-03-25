from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.continuous_demo.models import ContinuousDemoSession
from apps.operator_alerts.models import OperatorAlert, OperatorAlertSeverity, OperatorAlertStatus, OperatorDigest
from apps.operator_alerts.services import build_digest, emit_alert, run_default_alert_aggregation
from apps.operator_alerts.services.alerts import AlertEmitPayload
from apps.operator_queue.models import OperatorQueueItem
from apps.readiness_lab.models import ReadinessAssessmentRun, ReadinessProfile
from apps.real_data_sync.models import ProviderSyncRun
from apps.runtime_governor.models import RuntimeModeState, RuntimeStateStatus
from apps.safety_guard.models import SafetyPolicyConfig


class OperatorAlertsTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_create_and_dedupe_alert(self):
        first = emit_alert(AlertEmitPayload(
            alert_type='sync',
            severity='warning',
            title='Sync stale',
            summary='stale provider',
            source='real_sync',
            dedupe_key='sync:stale:kalshi',
            metadata={'a': 1},
        ))
        second = emit_alert(AlertEmitPayload(
            alert_type='sync',
            severity='high',
            title='Sync still stale',
            summary='still stale',
            source='real_sync',
            dedupe_key='sync:stale:kalshi',
            metadata={'b': 2},
        ))
        self.assertEqual(first.id, second.id)
        self.assertEqual(OperatorAlert.objects.count(), 1)
        second.refresh_from_db()
        self.assertEqual(second.severity, 'high')

    def test_acknowledge_and_resolve_endpoints(self):
        alert = OperatorAlert.objects.create(
            alert_type='runtime',
            severity='high',
            status='OPEN',
            title='runtime degraded',
            summary='x',
            source='runtime',
            first_seen_at=timezone.now(),
            last_seen_at=timezone.now(),
        )
        ack = self.client.post(reverse('operator_alerts:acknowledge', kwargs={'pk': alert.id}), {}, format='json')
        self.assertEqual(ack.status_code, 200)
        alert.refresh_from_db()
        self.assertEqual(alert.status, OperatorAlertStatus.ACKNOWLEDGED)

        resolve = self.client.post(reverse('operator_alerts:resolve', kwargs={'pk': alert.id}), {}, format='json')
        self.assertEqual(resolve.status_code, 200)
        alert.refresh_from_db()
        self.assertEqual(alert.status, OperatorAlertStatus.RESOLVED)

    def test_digest_build(self):
        now = timezone.now()
        OperatorAlert.objects.create(
            alert_type='runtime', severity='critical', status='OPEN', title='critical', summary='x', source='runtime', first_seen_at=now, last_seen_at=now,
        )
        digest = build_digest()
        self.assertIsInstance(digest, OperatorDigest)
        self.assertEqual(digest.critical_count, 1)

    def test_rebuild_generates_alerts_from_modules(self):
        OperatorQueueItem.objects.create(
            status='PENDING',
            source='semi_auto',
            queue_type='approval_required',
            priority='critical',
            headline='Urgent approval',
            summary='review now',
        )
        SafetyPolicyConfig.objects.create(name='default', kill_switch_enabled=True, status='KILL_SWITCH')
        RuntimeModeState.objects.create(current_mode='OBSERVE_ONLY', status=RuntimeStateStatus.DEGRADED)
        ProviderSyncRun.objects.create(provider='kalshi', sync_type='full', status='FAILED', started_at=timezone.now() - timedelta(hours=2), errors_count=1)
        profile = ReadinessProfile.objects.create(name='B', slug='b-profile', profile_type='balanced')
        ReadinessAssessmentRun.objects.create(readiness_profile=profile, status='NOT_READY', summary='not ready')
        ContinuousDemoSession.objects.create(session_status='FAILED', started_at=timezone.now() - timedelta(hours=1), finished_at=timezone.now(), total_errors=4, summary='unexpected failure')

        created = run_default_alert_aggregation()
        self.assertGreater(created, 0)
        self.assertTrue(OperatorAlert.objects.filter(dedupe_key='safety:kill_switch').exists())

    def test_endpoints(self):
        alert = OperatorAlert.objects.create(
            alert_type='queue', severity=OperatorAlertSeverity.WARNING, status='OPEN', title='Queue backlog', summary='many pending', source='operator_queue', first_seen_at=timezone.now(), last_seen_at=timezone.now(),
        )
        OperatorDigest.objects.create(digest_type='manual', window_start=timezone.now() - timedelta(hours=1), window_end=timezone.now(), summary='digest', alerts_count=1)

        list_response = self.client.get(reverse('operator_alerts:list'))
        detail_response = self.client.get(reverse('operator_alerts:detail', kwargs={'pk': alert.id}))
        summary_response = self.client.get(reverse('operator_alerts:summary'))
        digests_response = self.client.get(reverse('operator_alerts:digests'))
        digest_build = self.client.post(reverse('operator_alerts:build_digest'), {'digest_type': 'manual'}, format='json')
        rebuild = self.client.post(reverse('operator_alerts:rebuild'), {}, format='json')

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(summary_response.status_code, 200)
        self.assertEqual(digests_response.status_code, 200)
        self.assertEqual(digest_build.status_code, 201)
        self.assertEqual(rebuild.status_code, 200)
