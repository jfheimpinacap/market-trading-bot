from django.test import TestCase
from django.urls import reverse

from apps.approval_center.models import ApprovalRequest
from apps.approval_center.services import apply_decision
from apps.autonomy_campaign.models import AutonomyCampaignCheckpoint, AutonomyCampaignStatus, AutonomyCampaignStep
from apps.autonomy_manager.services.domains import sync_domain_catalog
from apps.autonomy_roadmap.services.plans import run_roadmap_plan
from apps.autonomy_scenario.services.simulation import run_simulation


class AutonomyCampaignTests(TestCase):
    def setUp(self):
        sync_domain_catalog()

    def test_create_campaign_from_roadmap_and_order(self):
        plan = run_roadmap_plan(requested_by='tests')
        response = self.client.post(
            reverse('autonomy_campaign:create'),
            data={'source_type': 'roadmap_plan', 'source_object_id': str(plan.id)},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertGreater(payload['total_steps'], 0)
        waves = [item['wave'] for item in payload['steps']]
        self.assertEqual(waves, sorted(waves))

    def test_create_campaign_from_scenario(self):
        run = run_simulation(requested_by='tests', notes='campaign source')
        response = self.client.post(
            reverse('autonomy_campaign:create'),
            data={'source_type': 'scenario_run', 'source_object_id': str(run.id)},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertGreaterEqual(response.json()['total_steps'], 0)

    def test_checkpoint_created_and_resume_after_approval(self):
        plan = run_roadmap_plan(requested_by='tests')
        create = self.client.post(
            reverse('autonomy_campaign:create'),
            data={'source_type': 'roadmap_plan', 'source_object_id': str(plan.id)},
            content_type='application/json',
        ).json()
        campaign_id = create['id']

        first_apply_step = AutonomyCampaignStep.objects.filter(campaign_id=campaign_id, action_type='APPLY_TRANSITION').order_by('step_order').first()
        first_apply_step.metadata = {**(first_apply_step.metadata or {}), 'require_approval': True}
        first_apply_step.save(update_fields=['metadata', 'updated_at'])

        campaign = self.client.post(reverse('autonomy_campaign:start', args=[campaign_id]), data={}, content_type='application/json')
        self.assertEqual(campaign.status_code, 200)
        self.assertEqual(campaign.json()['status'], 'BLOCKED')

        checkpoint = AutonomyCampaignCheckpoint.objects.filter(step=first_apply_step).first()
        approval = ApprovalRequest.objects.get(pk=checkpoint.metadata.get('approval_request_id'))
        apply_decision(approval=approval, decision='APPROVE')

        resumed = self.client.post(reverse('autonomy_campaign:resume', args=[campaign_id]), data={}, content_type='application/json')
        self.assertEqual(resumed.status_code, 200)

    def test_abort_campaign(self):
        plan = run_roadmap_plan(requested_by='tests')
        create = self.client.post(
            reverse('autonomy_campaign:create'),
            data={'source_type': 'roadmap_plan', 'source_object_id': str(plan.id)},
            content_type='application/json',
        ).json()

        abort_response = self.client.post(reverse('autonomy_campaign:abort', args=[create['id']]), data={'reason': 'operator_abort'}, content_type='application/json')
        self.assertEqual(abort_response.status_code, 200)
        self.assertEqual(abort_response.json()['status'], AutonomyCampaignStatus.ABORTED)

    def test_core_endpoints(self):
        plan = run_roadmap_plan(requested_by='tests')
        create = self.client.post(
            reverse('autonomy_campaign:create'),
            data={'source_type': 'roadmap_plan', 'source_object_id': str(plan.id)},
            content_type='application/json',
        )
        campaign_id = create.json()['id']

        actions = [
            self.client.get(reverse('autonomy_campaign:list')),
            self.client.get(reverse('autonomy_campaign:detail', args=[campaign_id])),
            self.client.get(reverse('autonomy_campaign:summary')),
            self.client.post(reverse('autonomy_campaign:start', args=[campaign_id]), data={}, content_type='application/json'),
            self.client.post(reverse('autonomy_campaign:resume', args=[campaign_id]), data={}, content_type='application/json'),
            self.client.post(reverse('autonomy_campaign:abort', args=[campaign_id]), data={}, content_type='application/json'),
        ]
        for response in actions:
            self.assertIn(response.status_code, [200])
