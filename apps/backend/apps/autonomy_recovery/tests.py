from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.approval_center.models import ApprovalRequest
from apps.autonomy_campaign.models import AutonomyCampaignCheckpointType
from apps.autonomy_campaign.services import create_campaign
from apps.autonomy_campaign.services.checkpoints import create_checkpoint
from apps.autonomy_recovery.models import RecoverySnapshot
from apps.autonomy_recovery.services.run import run_recovery_review
from apps.autonomy_roadmap.services.plans import run_roadmap_plan
from apps.incident_commander.models import IncidentRecord


class AutonomyRecoveryTests(TestCase):
    def _create_campaign(self, status: str = 'PAUSED', title: str = 'Recovery Campaign'):
        plan = run_roadmap_plan(requested_by='tests')
        campaign = create_campaign(
            source_type='roadmap_plan',
            source_object_id=str(plan.id),
            title=title,
            summary='recovery',
            metadata={'domains': ['rollout_controls']},
        )
        campaign.status = status
        campaign.save(update_fields=['status', 'updated_at'])
        return campaign

    def test_selects_paused_and_blocked_candidates(self):
        paused = self._create_campaign(status='PAUSED', title='Paused')
        blocked = self._create_campaign(status='BLOCKED', title='Blocked')
        response = self.client.get(reverse('autonomy_recovery:candidates'))
        self.assertEqual(response.status_code, 200)
        ids = {item['campaign'] for item in response.json()}
        self.assertIn(paused.id, ids)
        self.assertIn(blocked.id, ids)

    def test_snapshot_captures_pending_blockers(self):
        campaign = self._create_campaign(status='PAUSED')
        step = campaign.steps.order_by('step_order').first()
        checkpoint = create_checkpoint(step=step, checkpoint_type=AutonomyCampaignCheckpointType.APPROVAL_REQUIRED, summary='Pending approval')
        ApprovalRequest.objects.create(
            source_type='other',
            source_object_id=f'autonomy_campaign_checkpoint:{checkpoint.id}:recovery',
            title='Approval needed',
            summary='recovery approval',
            priority='HIGH',
            status='PENDING',
            requested_at=timezone.now(),
            metadata={'autonomy_campaign_id': campaign.id},
        )

        run_recovery_review(actor='tests')
        snapshot = RecoverySnapshot.objects.filter(campaign=campaign).latest('id')
        self.assertTrue(snapshot.approvals_pending)
        self.assertTrue(snapshot.checkpoints_pending)
        self.assertEqual(snapshot.recovery_status, 'KEEP_PAUSED')

    def test_ready_to_resume_when_clean(self):
        campaign = self._create_campaign(status='PAUSED')
        campaign.checkpoints.update(status='SATISFIED')
        run_recovery_review(actor='tests')
        snapshot = RecoverySnapshot.objects.filter(campaign=campaign).latest('id')
        self.assertEqual(snapshot.recovery_status, 'READY_TO_RESUME')

    def test_review_abort_or_close_for_degraded_aging_campaign(self):
        campaign = self._create_campaign(status='PAUSED')
        campaign.__class__.objects.filter(pk=campaign.pk).update(updated_at=timezone.now() - timedelta(hours=30))
        IncidentRecord.objects.create(
            incident_type='runtime_conflict',
            severity='critical',
            status='DEGRADED',
            title='Critical incident',
            source_app='tests',
            related_object_type='autonomy_campaign',
            related_object_id=str(campaign.id),
            first_seen_at=timezone.now(),
            last_seen_at=timezone.now(),
        )
        IncidentRecord.objects.create(
            incident_type='runtime_conflict',
            severity='critical',
            status='OPEN',
            title='Critical incident 2',
            source_app='tests',
            related_object_type='autonomy_campaign',
            related_object_id=str(campaign.id),
            first_seen_at=timezone.now(),
            last_seen_at=timezone.now(),
        )

        run_recovery_review(actor='tests')
        snapshot = RecoverySnapshot.objects.filter(campaign=campaign).latest('id')
        self.assertIn(snapshot.recovery_status, ['REVIEW_ABORT', 'CLOSE_CANDIDATE'])

    def test_summary_endpoint(self):
        self._create_campaign(status='PAUSED')
        self.client.post(reverse('autonomy_recovery:run_review'), data={}, content_type='application/json')
        response = self.client.get(reverse('autonomy_recovery:summary'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('candidate_count', response.json())
