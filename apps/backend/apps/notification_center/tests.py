from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.notification_center.models import (
    NotificationAutomationState,
    NotificationChannel,
    NotificationDelivery,
    NotificationDeliveryMode,
    NotificationDeliveryStatus,
    NotificationEscalationEvent,
    NotificationRule,
)
from apps.notification_center.services import run_digest_cycle, send_alert_notifications
from apps.operator_alerts.models import OperatorAlert, OperatorDigest
from apps.operator_alerts.services import emit_alert
from apps.operator_alerts.services.alerts import AlertEmitPayload


class NotificationCenterTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.channel = NotificationChannel.objects.create(name='Local UI', slug='local-ui', channel_type='ui_only', is_enabled=True)
        self.rule = NotificationRule.objects.create(
            name='Critical runtime immediate',
            delivery_mode='immediate',
            severity_threshold='high',
            cooldown_seconds=900,
            dedupe_window_seconds=600,
            match_criteria={'alert_types': ['runtime', 'safety']},
        )
        self.rule.channels.add(self.channel)
        self.digest_rule = NotificationRule.objects.create(
            name='Digest cycle rule',
            delivery_mode='digest',
            severity_threshold='warning',
            cooldown_seconds=60,
            dedupe_window_seconds=60,
            match_criteria={'digest_types': ['manual', 'cycle_window']},
        )
        self.digest_rule.channels.add(self.channel)
        NotificationAutomationState.objects.create(id=1, is_enabled=True, digest_interval_minutes=30, escalation_after_minutes=5)

    def _create_alert(self, **overrides):
        now = timezone.now()
        payload = {
            'alert_type': 'runtime',
            'severity': 'critical',
            'status': 'OPEN',
            'title': 'Runtime degraded',
            'summary': 'state degraded',
            'source': 'runtime',
            'dedupe_key': 'runtime:degraded',
            'first_seen_at': now - timedelta(minutes=10),
            'last_seen_at': now,
        }
        payload.update(overrides)
        return OperatorAlert.objects.create(**payload)

    def test_routing_by_severity_threshold(self):
        alert = self._create_alert(severity='warning')
        deliveries = send_alert_notifications(alert)
        self.assertEqual(len(deliveries), 0)

        alert.severity = 'high'
        alert.save(update_fields=['severity'])
        deliveries = send_alert_notifications(alert)
        self.assertEqual(len(deliveries), 1)
        self.assertEqual(deliveries[0].delivery_status, NotificationDeliveryStatus.SENT)

    def test_dedupe_suppresses_second_delivery(self):
        alert = self._create_alert()
        first = send_alert_notifications(alert)
        second = send_alert_notifications(alert)
        self.assertEqual(first[0].delivery_status, NotificationDeliveryStatus.SENT)
        self.assertEqual(second[0].delivery_status, NotificationDeliveryStatus.SUPPRESSED)

    def test_automatic_dispatch_on_emit_alert(self):
        deliveries_before = NotificationDelivery.objects.count()
        emit_alert(AlertEmitPayload(
            alert_type='runtime',
            severity='critical',
            title='Runtime stopped',
            summary='loop stopped unexpectedly',
            source='runtime',
            dedupe_key='runtime:stopped',
        ))
        self.assertGreater(NotificationDelivery.objects.count(), deliveries_before)
        delivery = NotificationDelivery.objects.order_by('-id').first()
        self.assertEqual(delivery.trigger_source, 'automatic')

    def test_run_digest_cycle_creates_digest_and_delivery(self):
        result = run_digest_cycle(force=True)
        self.assertTrue(result['digest_created'])
        digest = OperatorDigest.objects.get(pk=result['digest_id'])
        self.assertEqual(digest.digest_type, 'cycle_window')
        self.assertTrue(NotificationDelivery.objects.filter(related_digest=digest, delivery_mode=NotificationDeliveryMode.DIGEST).exists())

    def test_automation_enable_disable_endpoints(self):
        disable_response = self.client.post(reverse('notification_center:automation_disable'), {}, format='json')
        self.assertEqual(disable_response.status_code, 200)
        self.assertFalse(disable_response.json()['is_enabled'])

        enable_response = self.client.post(reverse('notification_center:automation_enable'), {}, format='json')
        self.assertEqual(enable_response.status_code, 200)
        self.assertTrue(enable_response.json()['is_enabled'])

    def test_run_automatic_dispatch_endpoint_and_escalation(self):
        stale_alert = self._create_alert(
            dedupe_key='runtime:stale-critical',
            last_seen_at=timezone.now() - timedelta(minutes=10),
            first_seen_at=timezone.now() - timedelta(minutes=20),
        )
        response = self.client.post(reverse('notification_center:run_automatic_dispatch'), {}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('dispatch', response.json())
        self.assertTrue(NotificationEscalationEvent.objects.filter(alert=stale_alert).exists())

    def test_manual_send_alert_endpoint(self):
        alert = self._create_alert()
        response = self.client.post(reverse('notification_center:send_alert', kwargs={'alert_id': alert.id}), {}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    def test_manual_send_digest_endpoint(self):
        digest = OperatorDigest.objects.create(
            digest_type='manual',
            window_start=timezone.now() - timedelta(hours=1),
            window_end=timezone.now(),
            summary='manual digest',
            alerts_count=2,
            critical_count=1,
        )
        response = self.client.post(reverse('notification_center:send_digest', kwargs={'digest_id': digest.id}), {}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    def test_summary_endpoint(self):
        alert = self._create_alert()
        send_alert_notifications(alert)
        response = self.client.get(reverse('notification_center:summary'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('deliveries_sent', data)
        self.assertGreaterEqual(data['deliveries_sent'], 1)
