from django.test import TestCase
<<<<<<< HEAD
from django.urls import reverse

from apps.approval_center.models import ApprovalRequest
from apps.autonomy_campaign.models import AutonomyCampaignStatus
from apps.autonomy_campaign.services import create_campaign
from apps.autonomy_operations.models import CampaignRuntimeSnapshot, OperationsRecommendation
from apps.autonomy_roadmap.services.plans import run_roadmap_plan


class AutonomyInterventionTests(TestCase):
    def _create_running_campaign(self, title='Intervention Campaign'):
        plan = run_roadmap_plan(requested_by='tests')
        campaign = create_campaign(source_type='roadmap_plan', source_object_id=str(plan.id), title=title, summary='test campaign')
        campaign.status = AutonomyCampaignStatus.RUNNING
        campaign.save(update_fields=['status', 'updated_at'])
        return campaign

    def test_create_manual_request(self):
        campaign = self._create_running_campaign()
        response = self.client.post(
            reverse('autonomy_intervention:create_request', args=[campaign.id]),
            data={'source_type': 'manual', 'requested_action': 'PAUSE_CAMPAIGN', 'rationale': 'Manual pause request'},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['requested_action'], 'PAUSE_CAMPAIGN')

    def test_block_invalid_resume_with_persistent_blockers(self):
        campaign = self._create_running_campaign()
        CampaignRuntimeSnapshot.objects.create(
            campaign=campaign,
            campaign_status='RUNNING',
            runtime_status='BLOCKED',
            blockers=['checkpoint_open'],
            incident_impact=0,
            degraded_impact=0,
        )
        request_row = self.client.post(
            reverse('autonomy_intervention:create_request', args=[campaign.id]),
            data={'source_type': 'manual', 'requested_action': 'RESUME_CAMPAIGN', 'rationale': 'Resume request'},
            content_type='application/json',
        ).json()

        execute = self.client.post(
            reverse('autonomy_intervention:execute_request', args=[request_row['id']]),
            data={'actor': 'tests'},
            content_type='application/json',
        )
        self.assertEqual(execute.status_code, 200)
        self.assertEqual(execute.json()['action_status'], 'BLOCKED')

    def test_pause_executes(self):
        campaign = self._create_running_campaign()
        request_row = self.client.post(
            reverse('autonomy_intervention:create_request', args=[campaign.id]),
            data={'source_type': 'manual', 'requested_action': 'PAUSE_CAMPAIGN', 'rationale': 'Pause for safety'},
            content_type='application/json',
        ).json()

        execute = self.client.post(reverse('autonomy_intervention:execute_request', args=[request_row['id']]), data={'actor': 'tests'}, content_type='application/json')
        self.assertEqual(execute.status_code, 200)
        self.assertEqual(execute.json()['action_status'], 'EXECUTED')
        campaign.refresh_from_db()
        self.assertEqual(campaign.status, 'PAUSED')

    def test_review_for_abort_opens_approval(self):
        campaign = self._create_running_campaign()
        request_row = self.client.post(
            reverse('autonomy_intervention:create_request', args=[campaign.id]),
            data={'source_type': 'manual', 'requested_action': 'REVIEW_FOR_ABORT', 'rationale': 'Need abort review'},
            content_type='application/json',
        ).json()

        execute = self.client.post(reverse('autonomy_intervention:execute_request', args=[request_row['id']]), data={'actor': 'tests'}, content_type='application/json')
        self.assertEqual(execute.status_code, 200)
        self.assertEqual(ApprovalRequest.objects.count(), 1)

    def test_continue_clearance_audited(self):
        campaign = self._create_running_campaign()
        request_row = self.client.post(
            reverse('autonomy_intervention:create_request', args=[campaign.id]),
            data={'source_type': 'manual', 'requested_action': 'CLEAR_TO_CONTINUE', 'rationale': 'Continue is safe'},
            content_type='application/json',
        ).json()

        execute = self.client.post(reverse('autonomy_intervention:execute_request', args=[request_row['id']]), data={'actor': 'tests'}, content_type='application/json')
        self.assertEqual(execute.status_code, 200)
        self.assertEqual(execute.json()['result_summary'].startswith('Continue clearance confirmed'), True)

    def test_run_review_and_summary(self):
        campaign = self._create_running_campaign()
        OperationsRecommendation.objects.create(
            recommendation_type='PAUSE_CAMPAIGN',
            target_campaign=campaign,
            rationale='Pause due to pressure',
            reason_codes=['pressure'],
            blockers=['incident'],
        )
        run = self.client.post(reverse('autonomy_intervention:run_review'), data={}, content_type='application/json')
        self.assertEqual(run.status_code, 200)
        self.assertGreaterEqual(run.json()['created_request_count'], 1)

        summary = self.client.get(reverse('autonomy_intervention:summary'))
        self.assertEqual(summary.status_code, 200)
        self.assertIn('open_request_count', summary.json())
=======
from django.utils import timezone
from rest_framework.test import APIClient

from apps.approval_center.models import ApprovalRequest
from apps.autonomy_campaign.models import AutonomyCampaign
from apps.autonomy_operations.models import OperationsRecommendation


class AutonomyInterventionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.campaign = AutonomyCampaign.objects.create(
            source_type='manual_bundle',
            source_object_id='1',
            title='Test campaign',
            summary='Campaign for intervention tests',
            status='RUNNING',
            total_steps=1,
        )

    def test_create_manual_request(self):
        resp = self.client.post(
            f'/api/autonomy-interventions/request/{self.campaign.id}/',
            {'requested_action': 'PAUSE_CAMPAIGN', 'source_type': 'manual', 'rationale': 'manual test'},
            format='json',
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['request_status'], 'OPEN')

    def test_block_invalid_resume_when_campaign_running(self):
        req = self.client.post(
            f'/api/autonomy-interventions/request/{self.campaign.id}/',
            {'requested_action': 'RESUME_CAMPAIGN', 'source_type': 'manual', 'rationale': 'resume test'},
            format='json',
        ).data
        resp = self.client.post(f"/api/autonomy-interventions/execute/{req['id']}/", {'actor': 'tester'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['action_status'], 'BLOCKED')

    def test_pause_executes(self):
        req = self.client.post(
            f'/api/autonomy-interventions/request/{self.campaign.id}/',
            {'requested_action': 'PAUSE_CAMPAIGN', 'source_type': 'manual'},
            format='json',
        ).data
        resp = self.client.post(f"/api/autonomy-interventions/execute/{req['id']}/", {'actor': 'tester'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['action_status'], 'EXECUTED')

    def test_review_for_abort_opens_approval(self):
        req = self.client.post(
            f'/api/autonomy-interventions/request/{self.campaign.id}/',
            {'requested_action': 'REVIEW_FOR_ABORT', 'source_type': 'manual'},
            format='json',
        ).data
        resp = self.client.post(f"/api/autonomy-interventions/execute/{req['id']}/", {'actor': 'tester'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['action_status'], 'EXECUTED')
        self.assertTrue(ApprovalRequest.objects.filter(source_object_id=f"intervention-request-{req['id']}").exists())

    def test_continue_clearance_audited(self):
        self.campaign.status = 'PAUSED'
        self.campaign.save(update_fields=['status', 'updated_at'])
        req = self.client.post(
            f'/api/autonomy-interventions/request/{self.campaign.id}/',
            {'requested_action': 'CLEAR_TO_CONTINUE', 'source_type': 'manual'},
            format='json',
        ).data
        resp = self.client.post(f"/api/autonomy-interventions/execute/{req['id']}/", {'actor': 'tester'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['action_status'], 'EXECUTED')
        self.assertIn('cleared to continue', resp.data['result_summary'].lower())

    def test_run_review_and_summary(self):
        OperationsRecommendation.objects.create(
            recommendation_type='PAUSE_CAMPAIGN',
            target_campaign=self.campaign,
            rationale='pause now',
            reason_codes=['risk'],
            blockers=['incident'],
            confidence='0.9',
        )
        run = self.client.post('/api/autonomy-interventions/run-review/', {'actor': 'tester'}, format='json')
        self.assertEqual(run.status_code, 200)
        self.assertGreaterEqual(run.data['created_requests'], 1)
        summary = self.client.get('/api/autonomy-interventions/summary/')
        self.assertEqual(summary.status_code, 200)
        self.assertIn('open_request_count', summary.data)
>>>>>>> origin/main
