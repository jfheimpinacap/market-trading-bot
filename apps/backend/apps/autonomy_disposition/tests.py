from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.approval_center.models import ApprovalRequest
from apps.autonomy_campaign.models import AutonomyCampaignStatus
from apps.autonomy_campaign.services import create_campaign
from apps.autonomy_disposition.models import CampaignDisposition
from apps.autonomy_disposition.services.run import run_disposition_review
from apps.autonomy_roadmap.services.plans import run_roadmap_plan
from apps.autonomy_recovery.models import RecoverySnapshot


class AutonomyDispositionTests(TestCase):
    def _create_campaign(self, *, status: str = 'COMPLETED', title: str = 'Disposition Campaign', metadata: dict | None = None):
        plan = run_roadmap_plan(requested_by='tests')
        campaign = create_campaign(
            source_type='roadmap_plan',
            source_object_id=str(plan.id),
            title=title,
            summary='disposition',
            metadata=metadata or {'domains': ['rollout_controls']},
        )
        campaign.status = status
        campaign.save(update_fields=['status', 'updated_at'])
        return campaign

    def test_candidates_select_close_abort_retire(self):
        close_campaign = self._create_campaign(status='COMPLETED', title='Close candidate')
        abort_campaign = self._create_campaign(status='PAUSED', title='Abort candidate')
        retire_campaign = self._create_campaign(status='FAILED', title='Retire candidate')
        RecoverySnapshot.objects.create(campaign=abort_campaign, base_campaign_status='PAUSED', recovery_status='REVIEW_ABORT', rationale='review abort')

        response = self.client.get(reverse('autonomy_disposition:candidates'))
        self.assertEqual(response.status_code, 200)
        by_campaign = {item['campaign']: item for item in response.json()}
        self.assertEqual(by_campaign[close_campaign.id]['disposition_readiness'], 'READY_TO_CLOSE')
        self.assertEqual(by_campaign[abort_campaign.id]['disposition_readiness'], 'READY_TO_ABORT')
        self.assertEqual(by_campaign[retire_campaign.id]['disposition_readiness'], 'READY_TO_RETIRE')

    def test_disposition_blocked_by_pending_approval(self):
        campaign = self._create_campaign(status='COMPLETED')
        ApprovalRequest.objects.create(
            source_type='other',
            source_object_id=f'autonomy_campaign:{campaign.id}:pending',
            title='Pending gate',
            summary='pending approval',
            priority='HIGH',
            status='PENDING',
            requested_at=timezone.now(),
            metadata={'autonomy_campaign_id': campaign.id},
        )
        run_disposition_review(actor='tests')
        disposition = CampaignDisposition.objects.filter(campaign=campaign).latest('id')
        self.assertEqual(disposition.disposition_status, 'APPROVAL_REQUIRED')

    def test_record_completion_or_close_when_clean(self):
        campaign = self._create_campaign(status='COMPLETED')
        run_disposition_review(actor='tests')
        disposition = CampaignDisposition.objects.filter(campaign=campaign).latest('id')
        self.assertIn(disposition.disposition_type, ['CLOSED', 'COMPLETED_RECORDED'])

    def test_request_approval_and_apply(self):
        campaign = self._create_campaign(status='FAILED', metadata={'retire_requested': True})
        run_disposition_review(actor='tests')
        request_response = self.client.post(
            reverse('autonomy_disposition:request_approval', kwargs={'campaign_id': campaign.id}),
            data={},
            content_type='application/json',
        )
        self.assertEqual(request_response.status_code, 200)
        disposition = CampaignDisposition.objects.filter(campaign=campaign).latest('id')
        approval = disposition.linked_approval_request
        approval.status = 'APPROVED'
        approval.save(update_fields=['status', 'updated_at'])

        apply_response = self.client.post(
            reverse('autonomy_disposition:apply', kwargs={'campaign_id': campaign.id}),
            data={},
            content_type='application/json',
        )
        self.assertEqual(apply_response.status_code, 200)
        disposition.refresh_from_db()
        campaign.refresh_from_db()
        self.assertEqual(disposition.disposition_status, 'APPLIED')
        self.assertTrue(campaign.metadata.get('retired', False))

    def test_summary_endpoint(self):
        self._create_campaign(status='COMPLETED')
        self.client.post(reverse('autonomy_disposition:run_review'), data={}, content_type='application/json')
        response = self.client.get(reverse('autonomy_disposition:summary'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('candidate_count', response.json())

    def test_apply_aborted_updates_campaign_status(self):
        campaign = self._create_campaign(status='PAUSED')
        RecoverySnapshot.objects.create(campaign=campaign, base_campaign_status='PAUSED', recovery_status='REVIEW_ABORT', rationale='abort')
        self.client.post(reverse('autonomy_disposition:run_review'), data={}, content_type='application/json')
        disposition = CampaignDisposition.objects.filter(campaign=campaign).latest('id')
        disposition.requires_approval = False
        disposition.disposition_status = 'READY'
        disposition.save(update_fields=['requires_approval', 'disposition_status', 'updated_at'])

        self.client.post(reverse('autonomy_disposition:apply', kwargs={'campaign_id': campaign.id}), data={}, content_type='application/json')
        campaign.refresh_from_db()
        self.assertEqual(campaign.status, AutonomyCampaignStatus.ABORTED)
