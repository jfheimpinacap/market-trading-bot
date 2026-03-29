from django.test import TestCase
from django.urls import reverse

from apps.autonomy_campaign.services import create_campaign
from apps.autonomy_manager.services.domains import sync_domain_catalog
from apps.autonomy_program.models import AutonomyProgramState
from apps.autonomy_roadmap.services.plans import run_roadmap_plan
from apps.autonomy_scheduler.models import CampaignAdmission, ChangeWindow


class AutonomyLaunchTests(TestCase):
    def setUp(self):
        sync_domain_catalog()

    def _create_campaign(self, *, title='Launch Candidate', metadata=None):
        plan = run_roadmap_plan(requested_by='tests')
        return create_campaign(
            source_type='roadmap_plan',
            source_object_id=str(plan.id),
            title=title,
            summary='launch-test',
            metadata=metadata or {'domains': ['rollout_controls']},
        )

    def _admit_campaign(self, campaign):
        return CampaignAdmission.objects.create(campaign=campaign, source_type='roadmap_plan', status='ADMITTED', priority_score=70, readiness_score=75)

    def test_candidates_only_include_admitted_or_ready(self):
        admitted = self._create_campaign(title='Admitted campaign')
        blocked = self._create_campaign(title='Blocked campaign')
        self._admit_campaign(admitted)
        CampaignAdmission.objects.create(campaign=blocked, source_type='roadmap_plan', status='BLOCKED')

        response = self.client.get(reverse('autonomy_launch:candidates'))
        self.assertEqual(response.status_code, 200)
        ids = {row['campaign'] for row in response.json()}
        self.assertIn(admitted.id, ids)
        self.assertNotIn(blocked.id, ids)

    def test_preflight_blocks_on_program_frozen(self):
        campaign = self._create_campaign(metadata={'domains': ['rollout_controls']})
        self._admit_campaign(campaign)
        AutonomyProgramState.objects.create(concurrency_posture='FROZEN')
        ChangeWindow.objects.create(name='safe', status='OPEN', window_type='normal_change')

        response = self.client.post(reverse('autonomy_launch:run_preflight'), data={}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        rec_types = {row['recommendation_type'] for row in response.json()['recommendations']}
        self.assertIn('BLOCK_START', rec_types)

    def test_wait_for_window_when_not_open(self):
        campaign = self._create_campaign()
        self._admit_campaign(campaign)
        ChangeWindow.objects.create(name='later', status='UPCOMING', window_type='normal_change')

        response = self.client.post(reverse('autonomy_launch:run_preflight'), data={}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        rec_types = {row['recommendation_type'] for row in response.json()['recommendations']}
        self.assertIn('WAIT_FOR_WINDOW', rec_types)

    def test_dependency_blocked_generates_hold_or_wait(self):
        dependency = self._create_campaign(title='Dependency')
        dependent = self._create_campaign(title='Dependent', metadata={'domains': ['rollout_controls'], 'depends_on_campaigns': [dependency.id]})
        self._admit_campaign(dependency)
        self._admit_campaign(dependent)
        ChangeWindow.objects.create(name='safe', status='OPEN', window_type='normal_change')

        response = self.client.post(reverse('autonomy_launch:run_preflight'), data={}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        dependent_rows = [row for row in response.json()['readiness'] if row['campaign'] == dependent.id]
        self.assertTrue(dependent_rows)
        self.assertIn(dependent_rows[0]['readiness_status'], ['WAITING', 'CAUTION'])

    def test_require_approval_for_sensitive_cases(self):
        campaign = self._create_campaign()
        self._admit_campaign(campaign)
        AutonomyProgramState.objects.create(concurrency_posture='HIGH_RISK')
        ChangeWindow.objects.create(name='safe', status='OPEN', window_type='normal_change')

        response = self.client.post(reverse('autonomy_launch:run_preflight'), data={}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        rec_types = {row['recommendation_type'] for row in response.json()['recommendations']}
        self.assertIn('REQUIRE_APPROVAL_TO_START', rec_types)

    def test_authorize_hold_and_summary_endpoints(self):
        campaign = self._create_campaign()
        self._admit_campaign(campaign)
        ChangeWindow.objects.create(name='safe', status='OPEN', window_type='normal_change')
        self.client.post(reverse('autonomy_launch:run_preflight'), data={}, content_type='application/json')

        auth_response = self.client.post(reverse('autonomy_launch:authorize', args=[campaign.id]), data={}, content_type='application/json')
        self.assertEqual(auth_response.status_code, 200)
        self.assertEqual(auth_response.json()['authorization_status'], 'AUTHORIZED')

        hold_response = self.client.post(reverse('autonomy_launch:hold', args=[campaign.id]), data={'rationale': 'operator hold'}, content_type='application/json')
        self.assertEqual(hold_response.status_code, 200)
        self.assertEqual(hold_response.json()['authorization_status'], 'HOLD')

        summary = self.client.get(reverse('autonomy_launch:summary'))
        self.assertEqual(summary.status_code, 200)
        self.assertIn('ready_count', summary.json())
