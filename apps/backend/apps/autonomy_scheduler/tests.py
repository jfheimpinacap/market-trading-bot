from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.autonomy_campaign.models import AutonomyCampaign
from apps.autonomy_campaign.services import create_campaign
from apps.autonomy_manager.services.domains import sync_domain_catalog
from apps.autonomy_program.models import AutonomyProgramState
from apps.autonomy_roadmap.services.plans import run_roadmap_plan
from apps.autonomy_scheduler.models import AdmissionRecommendation, CampaignAdmission, ChangeWindow
from apps.incident_commander.models import DegradedModeState, DegradedSystemState


class AutonomySchedulerTests(TestCase):
    def setUp(self):
        sync_domain_catalog()

    def _create_campaign(self, *, title: str, metadata=None) -> AutonomyCampaign:
        plan = run_roadmap_plan(requested_by='tests')
        return create_campaign(
            source_type='roadmap_plan',
            source_object_id=str(plan.id),
            title=title,
            summary='scheduler-test',
            metadata=metadata or {'domains': ['rollout_controls']},
        )

    def test_queue_consolidation(self):
        self._create_campaign(title='Queue candidate')
        response = self.client.get(reverse('autonomy_scheduler:queue'))
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.json()), 1)

    def test_window_resolution(self):
        ChangeWindow.objects.create(name='safe-now', status='OPEN', window_type='normal_change', max_new_admissions=2)
        response = self.client.get(reverse('autonomy_scheduler:windows'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]['status'], 'OPEN')

    def test_block_on_frozen_posture(self):
        self._create_campaign(title='Frozen campaign')
        AutonomyProgramState.objects.create(concurrency_posture='FROZEN')
        ChangeWindow.objects.create(name='safe-now', status='OPEN', window_type='normal_change', max_new_admissions=2)
        run = self.client.post(reverse('autonomy_scheduler:run_plan'), data={}, content_type='application/json')
        self.assertEqual(run.status_code, 200)
        recommendation_types = {item['recommendation_type'] for item in run.json()['recommendations']}
        self.assertIn('BLOCK_ADMISSION', recommendation_types)

    def test_dependency_based_defer(self):
        dependency = self._create_campaign(title='Dependency')
        dependent = self._create_campaign(title='Dependent', metadata={'domains': ['rollout_controls'], 'depends_on_campaigns': [dependency.id]})
        CampaignAdmission.objects.create(campaign=dependency, source_type='roadmap_plan', status='PENDING')
        CampaignAdmission.objects.create(campaign=dependent, source_type='roadmap_plan', status='PENDING')
        ChangeWindow.objects.create(name='safe-now', status='OPEN', window_type='normal_change', max_new_admissions=2)
        self.client.post(reverse('autonomy_scheduler:run_plan'), data={}, content_type='application/json')
        dependent_admission = CampaignAdmission.objects.get(campaign=dependent)
        self.assertEqual(dependent_admission.status, 'DEFERRED')

    def test_recommendation_safe_to_admit_or_wait_for_window(self):
        self._create_campaign(title='Candidate')
        response_no_window = self.client.post(reverse('autonomy_scheduler:run_plan'), data={}, content_type='application/json')
        recommendation_types = {item['recommendation_type'] for item in response_no_window.json()['recommendations']}
        self.assertIn('WAIT_FOR_WINDOW', recommendation_types)

        ChangeWindow.objects.create(name='safe-now', status='OPEN', window_type='normal_change', max_new_admissions=1)
        response_open = self.client.post(reverse('autonomy_scheduler:run_plan'), data={}, content_type='application/json')
        recommendation_types_open = {item['recommendation_type'] for item in response_open.json()['recommendations']}
        self.assertTrue('SAFE_TO_ADMIT_NEXT' in recommendation_types_open or 'REQUIRE_APPROVAL_TO_ADMIT' in recommendation_types_open)

    def test_admit_defer_and_summary_endpoints(self):
        campaign = self._create_campaign(title='Actionable')
        ChangeWindow.objects.create(name='safe-now', status='OPEN', window_type='normal_change', max_new_admissions=1)
        self.client.post(reverse('autonomy_scheduler:run_plan'), data={}, content_type='application/json')

        defer_response = self.client.post(
            reverse('autonomy_scheduler:defer', args=[campaign.id]),
            data={'reason': 'operator hold', 'deferred_until': timezone.now().isoformat()},
            content_type='application/json',
        )
        self.assertEqual(defer_response.status_code, 200)

        admit_response = self.client.post(reverse('autonomy_scheduler:admit', args=[campaign.id]), data={}, content_type='application/json')
        self.assertEqual(admit_response.status_code, 200)

        summary = self.client.get(reverse('autonomy_scheduler:summary'))
        self.assertEqual(summary.status_code, 200)
        self.assertIn('queue_counts', summary.json())
        self.assertTrue(AdmissionRecommendation.objects.exists())
