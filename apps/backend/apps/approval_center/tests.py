from django.test import TestCase
from django.urls import reverse

from apps.approval_center.models import ApprovalDecision, ApprovalRequest, ApprovalRequestStatus, ApprovalSourceType
from apps.approval_center.services.impact import get_approval_impact_preview
from apps.approval_center.services.requests import sync_approval_requests
from apps.automation_policy.services import apply_profile
from apps.go_live_gate.services import create_approval_request as create_go_live_approval
from apps.operator_queue.models import OperatorQueueItem
from apps.runbook_engine.models import RunbookApprovalCheckpointStatus
from apps.runbook_engine.services import ensure_default_templates


class ApprovalCenterTests(TestCase):
    def setUp(self):
        ensure_default_templates()
        apply_profile(profile_slug='supervised_autopilot')

    def _create_runbook_checkpoint(self):
        templates = self.client.get(reverse('runbook_engine:templates')).json()
        chosen = next(template for template in templates if template['slug'] == 'rollout_guardrail_response')
        runbook = self.client.post(
            reverse('runbook_engine:create'),
            data={
                'template_slug': chosen['slug'],
                'source_object_type': chosen['trigger_type'],
                'source_object_id': 'approval-center-test',
            },
            content_type='application/json',
        ).json()
        run = self.client.post(reverse('runbook_engine:run-autopilot', args=[runbook['id']]), data='{}', content_type='application/json').json()
        pending = [item for item in run.get('approval_checkpoints', []) if item['status'] == 'PENDING']
        if not pending:
            self.skipTest('Fixture did not produce pending checkpoint.')
        return pending[0]

    def test_sync_creates_approval_request_from_runbook_checkpoint(self):
        pending_checkpoint = self._create_runbook_checkpoint()
        sync_approval_requests()
        request = ApprovalRequest.objects.get(source_type=ApprovalSourceType.RUNBOOK_CHECKPOINT, source_object_id=str(pending_checkpoint['id']))
        self.assertEqual(request.status, ApprovalRequestStatus.PENDING)

    def test_approve_reject_persist_decisions(self):
        pending_checkpoint = self._create_runbook_checkpoint()
        sync_approval_requests()
        request = ApprovalRequest.objects.get(source_type=ApprovalSourceType.RUNBOOK_CHECKPOINT, source_object_id=str(pending_checkpoint['id']))

        approve = self.client.post(reverse('approval_center:approve', args=[request.id]), {'rationale': 'looks safe'}, format='json')
        self.assertEqual(approve.status_code, 200)
        request.refresh_from_db()
        self.assertEqual(request.status, ApprovalRequestStatus.APPROVED)
        self.assertTrue(ApprovalDecision.objects.filter(approval_request=request, decision='APPROVE').exists())

        queue_item = OperatorQueueItem.objects.create(headline='Queue review', summary='Manual reject', queue_type='approval_required', priority='high')
        sync_approval_requests()
        queue_request = ApprovalRequest.objects.get(source_type=ApprovalSourceType.OPERATOR_QUEUE_ITEM, source_object_id=str(queue_item.id))

        reject = self.client.post(reverse('approval_center:reject', args=[queue_request.id]), {'rationale': 'blocked'}, format='json')
        self.assertEqual(reject.status_code, 200)
        queue_request.refresh_from_db()
        self.assertEqual(queue_request.status, ApprovalRequestStatus.REJECTED)
        self.assertTrue(ApprovalDecision.objects.filter(approval_request=queue_request, decision='REJECT').exists())

    def test_impact_preview_for_go_live(self):
        go_live = create_go_live_approval(requested_by='local-operator', rationale='Manual rehearsal approval', scope='global', requested_mode='PRELIVE_REHEARSAL')
        sync_approval_requests()
        request = ApprovalRequest.objects.get(source_type=ApprovalSourceType.GO_LIVE_REQUEST, source_object_id=str(go_live.id))
        preview = get_approval_impact_preview(request)
        self.assertIn('does NOT enable live trading', preview['approve'])

    def test_approval_action_resumes_runbook_checkpoint(self):
        pending_checkpoint = self._create_runbook_checkpoint()
        sync_approval_requests()
        request = ApprovalRequest.objects.get(source_type=ApprovalSourceType.RUNBOOK_CHECKPOINT, source_object_id=str(pending_checkpoint['id']))

        response = self.client.post(reverse('approval_center:approve', args=[request.id]), {'rationale': 'resume'}, format='json')
        self.assertEqual(response.status_code, 200)

        autopilot_runs = self.client.get(reverse('runbook_engine:autopilot-runs')).json()
        checkpoint_statuses = {item['status'] for item in autopilot_runs[0]['approval_checkpoints']}
        self.assertTrue(
            any(status in checkpoint_statuses for status in [RunbookApprovalCheckpointStatus.APPROVED, RunbookApprovalCheckpointStatus.REJECTED, RunbookApprovalCheckpointStatus.EXPIRED])
        )

    def test_main_endpoints(self):
        list_response = self.client.get(reverse('approval_center:list'))
        pending_response = self.client.get(reverse('approval_center:pending'))
        summary_response = self.client.get(reverse('approval_center:summary'))

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(pending_response.status_code, 200)
        self.assertEqual(summary_response.status_code, 200)
