from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.notification_center.models import NotificationChannel, NotificationDelivery, NotificationDeliveryStatus, NotificationRule
from apps.notification_center.services import send_alert_notifications
from apps.operator_alerts.models import OperatorAlert, OperatorDigest


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
            name='Manual digest rule',
            delivery_mode='digest',
            severity_threshold='warning',
            cooldown_seconds=60,
            dedupe_window_seconds=60,
            match_criteria={'digest_types': ['manual']},
        )
        self.digest_rule.channels.add(self.channel)

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

    def test_delivery_record_created(self):
        alert = self._create_alert()
        send_alert_notifications(alert)
        self.assertEqual(NotificationDelivery.objects.count(), 1)
        record = NotificationDelivery.objects.first()
        self.assertEqual(record.related_alert_id, alert.id)
        self.assertEqual(record.channel_id, self.channel.id)

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
        self.assertEqual(data['deliveries_sent'], 1)
