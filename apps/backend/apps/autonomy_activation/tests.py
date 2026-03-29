from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.autonomy_campaign.models import AutonomyCampaignStatus
from apps.autonomy_campaign.services import create_campaign
from apps.autonomy_launch.models import LaunchAuthorization
from apps.autonomy_manager.services.domains import sync_domain_catalog
from apps.autonomy_program.models import AutonomyProgramState
from apps.autonomy_roadmap.services.plans import run_roadmap_plan
from apps.autonomy_scheduler.models import ChangeWindow
from apps.incident_commander.models import IncidentRecord


class AutonomyActivationTests(TestCase):
    def setUp(self):
        sync_domain_catalog()

    def _create_campaign(self, title='Activation Campaign', metadata=None):
        plan = run_roadmap_plan(requested_by='tests')
        return create_campaign(
            source_type='roadmap_plan',
            source_object_id=str(plan.id),
            title=title,
            summary='activation-test',
            metadata=metadata or {'domains': ['rollout_controls']},
        )

    def _authorize(self, campaign, expires_in_hours=2):
        return LaunchAuthorization.objects.create(
            campaign=campaign,
            authorization_status='AUTHORIZED',
            authorization_type='normal_start',
            rationale='tests authorization',
            reason_codes=['TEST_AUTH'],
            authorized_by='tests',
            authorized_at=timezone.now(),
            expires_at=timezone.now() + timedelta(hours=expires_in_hours),
        )

    def test_candidates_selection_with_valid_authorization(self):
        campaign = self._create_campaign()
        self._authorize(campaign)
        ChangeWindow.objects.create(name='safe-now', status='OPEN', window_type='normal_change')

        response = self.client.get(reverse('autonomy_activation:candidates'))
        self.assertEqual(response.status_code, 200)
        ids = {row['campaign'] for row in response.json()}
        self.assertIn(campaign.id, ids)

    def test_block_when_authorization_expired(self):
        campaign = self._create_campaign()
        self._authorize(campaign, expires_in_hours=-1)

        response = self.client.post(reverse('autonomy_activation:dispatch', args=[campaign.id]), data={}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['activation_status'], 'EXPIRED')

    def test_block_when_program_frozen_or_critical_incident(self):
        campaign = self._create_campaign()
        self._authorize(campaign)
        AutonomyProgramState.objects.create(concurrency_posture='FROZEN')
        ChangeWindow.objects.create(name='safe-now', status='OPEN', window_type='normal_change')

        response = self.client.post(reverse('autonomy_activation:dispatch', args=[campaign.id]), data={}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['activation_status'], 'BLOCKED')

        campaign2 = self._create_campaign(title='Incident blocked campaign')
        self._authorize(campaign2)
        IncidentRecord.objects.create(
            incident_type='runtime_conflict',
            severity='critical',
            status='OPEN',
            title='Critical incident',
            source_app='tests',
            first_seen_at=timezone.now(),
            last_seen_at=timezone.now(),
        )
        response2 = self.client.post(reverse('autonomy_activation:dispatch', args=[campaign2.id]), data={}, content_type='application/json')
        self.assertEqual(response2.status_code, 200)
        self.assertEqual(response2.json()['activation_status'], 'BLOCKED')

    def test_block_when_campaign_already_running(self):
        campaign = self._create_campaign()
        self._authorize(campaign)
        campaign.status = AutonomyCampaignStatus.RUNNING
        campaign.save(update_fields=['status', 'updated_at'])

        response = self.client.post(reverse('autonomy_activation:dispatch', args=[campaign.id]), data={}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['activation_status'], 'BLOCKED')

    def test_dispatch_success_creates_started_activation(self):
        campaign = self._create_campaign()
        self._authorize(campaign)
        ChangeWindow.objects.create(name='safe-now', status='OPEN', window_type='normal_change')

        response = self.client.post(reverse('autonomy_activation:dispatch', args=[campaign.id]), data={}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['activation_status'], 'STARTED')

    def test_dispatch_failure_persists_failed_activation(self):
        campaign = self._create_campaign(metadata={'domains': ['rollout_controls']})
        self._authorize(campaign)
        ChangeWindow.objects.create(name='safe-now', status='OPEN', window_type='normal_change')
        with patch('apps.autonomy_activation.services.control.dispatch_campaign_start', side_effect=RuntimeError('boom')):
            response = self.client.post(reverse('autonomy_activation:dispatch', args=[campaign.id]), data={}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['activation_status'], 'FAILED')
        self.assertIn('boom', response.json()['failure_message'].lower())

    def test_summary_endpoint(self):
        campaign = self._create_campaign()
        self._authorize(campaign)
        ChangeWindow.objects.create(name='safe-now', status='OPEN', window_type='normal_change')
        self.client.post(reverse('autonomy_activation:run_dispatch_review'), data={}, content_type='application/json')

        response = self.client.get(reverse('autonomy_activation:summary'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('ready_count', response.json())
