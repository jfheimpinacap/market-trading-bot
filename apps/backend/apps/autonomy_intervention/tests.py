from django.test import TestCase
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
