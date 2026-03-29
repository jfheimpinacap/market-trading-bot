from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.approval_center.models import ApprovalRequest
from apps.autonomy_campaign.models import AutonomyCampaignCheckpointType
from apps.autonomy_campaign.services import create_campaign
from apps.autonomy_campaign.services.checkpoints import create_checkpoint
from apps.autonomy_operations.models import CampaignAttentionSignal, CampaignRuntimeSnapshot, OperationsRecommendation
from apps.autonomy_operations.services.run import run_monitor_cycle
from apps.autonomy_roadmap.services.plans import run_roadmap_plan
from apps.incident_commander.models import IncidentRecord


class AutonomyOperationsTests(TestCase):
    def _create_running_campaign(self, title='Ops Campaign'):
        plan = run_roadmap_plan(requested_by='tests')
        campaign = create_campaign(
            source_type='roadmap_plan',
            source_object_id=str(plan.id),
            title=title,
            summary='ops',
            metadata={'domains': ['rollout_controls']},
        )
        campaign.status = 'RUNNING'
        campaign.save(update_fields=['status', 'updated_at'])
        return campaign

    def test_runtime_snapshot_for_active_campaigns(self):
        self._create_running_campaign()
        result = run_monitor_cycle(actor='tests')
        self.assertEqual(result['run'].active_campaign_count, 1)
        self.assertEqual(CampaignRuntimeSnapshot.objects.count(), 1)

    def test_stalled_campaign_detection(self):
        campaign = self._create_running_campaign()
        campaign.__class__.objects.filter(pk=campaign.pk).update(updated_at=timezone.now() - timedelta(hours=2))

        run_monitor_cycle(actor='tests')
        snapshot = CampaignRuntimeSnapshot.objects.latest('id')
        self.assertEqual(snapshot.campaign_id, campaign.id)
        self.assertEqual(snapshot.runtime_status, 'STALLED')

    def test_waiting_approval_runtime_and_signal(self):
        campaign = self._create_running_campaign()
        step = campaign.steps.order_by('step_order').first()
        checkpoint = create_checkpoint(step=step, checkpoint_type=AutonomyCampaignCheckpointType.APPROVAL_REQUIRED, summary='Pending approval for ops test')
        approval = ApprovalRequest.objects.create(
            source_type='other',
            source_object_id=f'autonomy_campaign_checkpoint:{checkpoint.id}:ops',
            title='Approval needed',
            summary='ops approval',
            priority='HIGH',
            status='PENDING',
            requested_at=timezone.now(),
            metadata={'autonomy_campaign_id': campaign.id},
        )
        checkpoint.metadata = {**(checkpoint.metadata or {}), 'approval_request_id': approval.id}
        checkpoint.save(update_fields=['metadata', 'updated_at'])

        run_monitor_cycle(actor='tests')
        snapshot = CampaignRuntimeSnapshot.objects.latest('id')
        self.assertEqual(snapshot.runtime_status, 'WAITING_APPROVAL')
        self.assertGreaterEqual(snapshot.pending_approvals_count, 1)

    def test_critical_incident_impacts_recommendation(self):
        campaign = self._create_running_campaign()
        IncidentRecord.objects.create(
            incident_type='runtime_conflict',
            severity='critical',
            status='OPEN',
            title='Critical runtime incident',
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
            title='Critical runtime incident 2',
            source_app='tests',
            related_object_type='autonomy_campaign',
            related_object_id=str(campaign.id),
            first_seen_at=timezone.now(),
            last_seen_at=timezone.now(),
        )

        run_monitor_cycle(actor='tests')
        rec = OperationsRecommendation.objects.filter(target_campaign=campaign).latest('id')
        self.assertEqual(rec.recommendation_type, 'REVIEW_FOR_ABORT')

    def test_recommendation_continue_for_healthy_campaign(self):
        campaign = self._create_running_campaign()
        campaign.checkpoints.update(status='SATISFIED')
        run_monitor_cycle(actor='tests')
        rec = OperationsRecommendation.objects.filter(target_campaign=campaign).latest('id')
        self.assertIn(rec.recommendation_type, ['CONTINUE_CAMPAIGN', 'CLEAR_TO_CONTINUE'])

    def test_acknowledge_signal_endpoint(self):
        self._create_running_campaign()
        run_monitor_cycle(actor='tests')
        signal = CampaignAttentionSignal.objects.filter(status='OPEN').first()
        if signal is None:
            self.skipTest('No open signals generated for this fixture.')

        response = self.client.post(reverse('autonomy_operations:acknowledge_signal', args=[signal.id]), data={}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ACKNOWLEDGED')

    def test_summary_endpoint(self):
        self._create_running_campaign()
        self.client.post(reverse('autonomy_operations:run_monitor'), data={}, content_type='application/json')
        response = self.client.get(reverse('autonomy_operations:summary'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('active_campaign_count', response.json())
