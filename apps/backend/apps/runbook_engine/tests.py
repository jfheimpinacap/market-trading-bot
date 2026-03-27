from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.certification_board.models import CertificationEvidenceSnapshot, CertificationLevel, CertificationRecommendationCode, CertificationRun, CertificationRunStatus, OperatingEnvelope
from apps.incident_commander.models import IncidentRecord
from apps.operator_queue.models import OperatorQueueItem, OperatorQueueStatus
from apps.runbook_engine.models import RunbookInstance
from apps.runbook_engine.services import create_runbook_instance, ensure_default_templates, recommend_runbooks


class RunbookEngineTests(TestCase):
    def setUp(self):
        ensure_default_templates()

    def test_create_runbook_from_template(self):
        template_res = self.client.get(reverse('runbook_engine:templates'))
        self.assertEqual(template_res.status_code, 200)
        template_slug = template_res.json()[0]['slug']

        res = self.client.post(
            reverse('runbook_engine:create'),
            data={
                'template_slug': template_slug,
                'source_object_type': 'incident',
                'source_object_id': '1',
                'priority': 'HIGH',
            },
            content_type='application/json',
        )
        self.assertEqual(res.status_code, 201)
        payload = res.json()
        self.assertGreater(len(payload['steps']), 0)
        self.assertEqual(payload['steps'][0]['status'], 'READY')

    def test_step_progression(self):
        template = next(t for t in self.client.get(reverse('runbook_engine:templates')).json() if t['slug'] == 'queue_pressure_relief')
        create_res = self.client.post(
            reverse('runbook_engine:create'),
            data={
                'template_slug': template['slug'],
                'source_object_type': 'operator_queue',
                'source_object_id': 'summary',
            },
            content_type='application/json',
        )
        runbook_id = create_res.json()['id']
        step_id = create_res.json()['steps'][0]['id']

        step_res = self.client.post(reverse('runbook_engine:run-step', args=[runbook_id, step_id]), data='{}', content_type='application/json')
        self.assertEqual(step_res.status_code, 200)
        runbook_payload = step_res.json()['runbook']
        self.assertIn(runbook_payload['status'], ['IN_PROGRESS', 'OPEN'])

    def test_recommendation_matching(self):
        IncidentRecord.objects.create(
            incident_type='rollout_guardrail',
            severity='critical',
            status='OPEN',
            title='Critical rollout incident',
            summary='Guardrail breached',
            source_app='rollout_manager',
            first_seen_at=timezone.now(),
            last_seen_at=timezone.now(),
            dedupe_key='test-critical-rollout',
        )

        recommendations = recommend_runbooks()
        slugs = {item['template_slug'] for item in recommendations}
        self.assertIn('incident_mission_control_pause', slugs)

    def test_summary_endpoint(self):
        template_slug = 'degraded_mode_recovery'
        self.client.post(
            reverse('runbook_engine:create'),
            data={
                'template_slug': template_slug,
                'source_object_type': 'degraded_mode',
                'source_object_id': 'active',
            },
            content_type='application/json',
        )
        summary_res = self.client.get(reverse('runbook_engine:summary'))
        self.assertEqual(summary_res.status_code, 200)
        self.assertIn('counts', summary_res.json())

    def test_recommendations_for_certification_downgrade(self):
        snapshot = CertificationEvidenceSnapshot.objects.create()
        envelope = OperatingEnvelope.objects.create()
        CertificationRun.objects.create(
            status=CertificationRunStatus.COMPLETED,
            decision_mode='RECOMMENDATION_ONLY',
            certification_level=CertificationLevel.REMEDIATION_REQUIRED,
            recommendation_code=CertificationRecommendationCode.REQUIRE_REMEDIATION,
            confidence=0.8,
            rationale='Need remediation',
            evidence_snapshot=snapshot,
            operating_envelope=envelope,
        )

        res = self.client.get(reverse('runbook_engine:recommendations'))
        self.assertEqual(res.status_code, 200)
        slugs = {item['template_slug'] for item in res.json()['results']}
        self.assertIn('certification_downgrade_review', slugs)

    def test_operator_queue_pressure_recommendation(self):
        for i in range(7):
            OperatorQueueItem.objects.create(
                status=OperatorQueueStatus.PENDING,
                source='runbook_test',
                queue_type='blocked_review',
                headline=f'item-{i}',
                summary='x',
                rationale='x',
                priority='high',
            )

        res = self.client.get(reverse('runbook_engine:recommendations'))
        self.assertEqual(res.status_code, 200)
        slugs = {item['template_slug'] for item in res.json()['results']}
        self.assertIn('queue_pressure_relief', slugs)
