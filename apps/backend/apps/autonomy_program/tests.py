from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.autonomy_campaign.models import AutonomyCampaign
from apps.autonomy_campaign.services import create_campaign
from apps.autonomy_manager.models import AutonomyDomain
from apps.autonomy_manager.services.domains import sync_domain_catalog
from apps.autonomy_program.models import CampaignConcurrencyRule, CampaignConcurrencyRuleType, ProgramRecommendation
from apps.autonomy_program.services.control import run_program_review
from apps.autonomy_roadmap.services.plans import run_roadmap_plan
from apps.incident_commander.models import DegradedModeState, DegradedSystemState


class AutonomyProgramTests(TestCase):
    def setUp(self):
        sync_domain_catalog()

    def _create_running_campaign(self, *, source_object_id: str, title: str, domain_slug: str = 'rollout_controls') -> AutonomyCampaign:
        plan = run_roadmap_plan(requested_by='tests')
        campaign = create_campaign(
            source_type='roadmap_plan',
            source_object_id=str(plan.id),
            title=title,
            summary='test campaign',
            metadata={'domains': [domain_slug]},
        )
        domain = AutonomyDomain.objects.filter(slug=domain_slug).first()
        first_step = campaign.steps.order_by('step_order').first()
        if first_step and domain:
            first_step.domain = domain
            first_step.status = 'RUNNING'
            first_step.save(update_fields=['domain', 'status', 'updated_at'])
        campaign.status = 'RUNNING'
        campaign.save(update_fields=['status', 'updated_at'])
        return campaign

    def test_state_consolidation_basic(self):
        self._create_running_campaign(source_object_id='c-1', title='Campaign one', domain_slug='rollout_controls')
        response = self.client.get(reverse('autonomy_program:state'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['state']['active_campaigns_count'], 1)
        self.assertIn(payload['state']['concurrency_posture'], ['NORMAL', 'CONSTRAINED'])

    def test_incompatible_concurrent_campaign_detection(self):
        self._create_running_campaign(source_object_id='c-1', title='Execution campaign', domain_slug='rollout_controls')
        self._create_running_campaign(source_object_id='c-2', title='Bridge campaign', domain_slug='bridge_validation_review')
        review = run_program_review(actor='tests')
        pause_recommendations = [item for item in review['recommendations'] if item.recommendation_type == 'PAUSE_CAMPAIGN']
        self.assertGreaterEqual(len(pause_recommendations), 1)

    def test_max_active_campaigns_enforcement(self):
        rule = CampaignConcurrencyRule.objects.filter(rule_type=CampaignConcurrencyRuleType.MAX_ACTIVE_CAMPAIGNS).first()
        if rule:
            rule.config = {'max_active_campaigns': 1}
            rule.save(update_fields=['config', 'updated_at'])
        else:
            CampaignConcurrencyRule.objects.create(
                rule_type=CampaignConcurrencyRuleType.MAX_ACTIVE_CAMPAIGNS,
                scope='global',
                config={'max_active_campaigns': 1},
                rationale='tests',
            )
        self._create_running_campaign(source_object_id='c-1', title='Campaign one', domain_slug='rollout_controls')
        self._create_running_campaign(source_object_id='c-2', title='Campaign two', domain_slug='incident_response')
        review = run_program_review(actor='tests', apply_pause_gating=False)
        reason_codes = [code for rec in review['recommendations'] for code in rec.reason_codes]
        self.assertIn('MAX_ACTIVE_EXCEEDED', reason_codes)

    def test_hold_recommendation_on_degraded_posture(self):
        self._create_running_campaign(source_object_id='c-1', title='Campaign one', domain_slug='rollout_controls')
        DegradedModeState.objects.create(
            state=DegradedSystemState.DEFENSIVE_ONLY,
            mission_control_paused=True,
            auto_execution_enabled=False,
            rollout_enabled=False,
            degraded_modules=['rollout_controls'],
            reasons=['test degraded posture'],
            activated_at=timezone.now(),
        )
        response = self.client.post(reverse('autonomy_program:run_review'), data={'actor': 'tests', 'apply_pause_gating': False}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        recommendation_types = {row['recommendation_type'] for row in response.json()['recommendations']}
        self.assertTrue('WAIT_FOR_STABILIZATION' in recommendation_types or 'HOLD_NEW_CAMPAIGNS' in recommendation_types)

    def test_summary_endpoint(self):
        self._create_running_campaign(source_object_id='c-1', title='Campaign one', domain_slug='rollout_controls')
        run_program_review(actor='tests', apply_pause_gating=False)
        response = self.client.get(reverse('autonomy_program:summary'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('concurrency_posture', response.json())

    def test_main_endpoints_work(self):
        self._create_running_campaign(source_object_id='c-1', title='Campaign one', domain_slug='rollout_controls')
        actions = [
            self.client.get(reverse('autonomy_program:state')),
            self.client.get(reverse('autonomy_program:rules')),
            self.client.post(reverse('autonomy_program:run_review'), data={}, content_type='application/json'),
            self.client.get(reverse('autonomy_program:recommendations')),
            self.client.get(reverse('autonomy_program:health')),
            self.client.get(reverse('autonomy_program:summary')),
        ]
        for response in actions:
            self.assertEqual(response.status_code, 200)

    def test_pause_gating_marks_campaign_blocked(self):
        campaign = self._create_running_campaign(source_object_id='c-1', title='Execution campaign', domain_slug='rollout_controls')
        self._create_running_campaign(source_object_id='c-2', title='Bridge campaign', domain_slug='bridge_validation_review')
        run_program_review(actor='tests', apply_pause_gating=True)
        campaign.refresh_from_db()
        self.assertEqual(campaign.status, 'BLOCKED')
        self.assertTrue(ProgramRecommendation.objects.filter(recommendation_type='PAUSE_CAMPAIGN').exists())
