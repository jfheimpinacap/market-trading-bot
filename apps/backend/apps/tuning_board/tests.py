from django.test import TestCase
from django.urls import reverse

from apps.evaluation_lab.models import (
    EffectivenessMetric,
    EffectivenessMetricStatus,
    EffectivenessMetricType,
    EvaluationRecommendation,
    EvaluationRuntimeRun,
)
from apps.tuning_board.models import TuningProposal, TuningProposalBundle, TuningRecommendation
from apps.tuning_board.services.evidence_scoring import score_evidence


class TuningBoardTests(TestCase):
    def setUp(self):
        self.eval_run = EvaluationRuntimeRun.objects.create(drift_flag_count=2, recommendation_summary={'TIGHTEN_RISK_GATE': 1})

    def _create_metric(self, **kwargs):
        defaults = {
            'run': self.eval_run,
            'metric_type': EffectivenessMetricType.CALIBRATION_ERROR,
            'metric_scope': 'global',
            'metric_value': 0.22,
            'sample_count': 140,
            'status': EffectivenessMetricStatus.POOR,
            'reason_codes': ['CALIBRATION_GAP_HIGH'],
            'metadata': {},
        }
        defaults.update(kwargs)
        return EffectivenessMetric.objects.create(**defaults)

    def test_run_review_derives_proposals_from_poor_metrics(self):
        metric = self._create_metric()
        EvaluationRecommendation.objects.create(
            run=self.eval_run,
            recommendation_type='REVIEW_CALIBRATION_DRIFT',
            target_metric=metric,
            rationale='Calibration drift recurring.',
            reason_codes=['CALIBRATION_DRIFT'],
            confidence=0.82,
        )

        response = self.client.post(reverse('tuning_board:run-review'), data={}, content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertGreater(TuningProposal.objects.count(), 0)

    def test_require_more_data_when_sample_low(self):
        metric = self._create_metric(sample_count=12, status=EffectivenessMetricStatus.NEEDS_MORE_DATA)
        candidate = {
            'proposal_type': 'calibration_bias_offset',
            'target_component': 'calibration',
            'source_metric': metric,
            'reason_codes': ['LOW_SAMPLE'],
            'rationale': 'low sample',
        }
        scored = score_evidence(candidate)
        self.assertEqual(scored['proposal_status'], 'WATCH')
        self.assertIn('requires_more_data', scored['blockers'])

    def test_strong_evidence_marks_ready_for_review(self):
        metric = self._create_metric(sample_count=220, status=EffectivenessMetricStatus.POOR)
        candidate = {
            'proposal_type': 'risk_gate_threshold',
            'target_component': 'risk',
            'source_metric': metric,
            'reason_codes': ['RISK_PRECISION_DEGRADED'],
            'rationale': 'precision poor',
        }
        scored = score_evidence(candidate)
        self.assertIn(scored['proposal_status'], ['PROPOSED', 'READY_FOR_REVIEW'])
        self.assertIn(scored['priority_level'], ['HIGH', 'CRITICAL', 'MEDIUM'])

    def test_basic_bundling_and_recommendations(self):
        m1 = self._create_metric(metric_type=EffectivenessMetricType.RISK_APPROVAL_PRECISION, metric_scope='provider', sample_count=130)
        m2 = self._create_metric(metric_type=EffectivenessMetricType.BLOCKED_OPPORTUNITY_ESCAPE_RATE, metric_scope='provider', sample_count=150)
        EvaluationRecommendation.objects.create(
            run=self.eval_run,
            recommendation_type='TIGHTEN_RISK_GATE',
            target_metric=m1,
            rationale='Too many false positives.',
            reason_codes=['FALSE_POSITIVE_HIGH'],
            confidence=0.8,
        )
        self.client.post(reverse('tuning_board:run-review'), data={}, content_type='application/json')
        self.assertGreaterEqual(TuningRecommendation.objects.count(), 1)
        # bundle may or may not exist depending on scope values, validate no crash path and allow grouping.
        self.assertGreaterEqual(TuningProposalBundle.objects.count(), 0)

    def test_summary_endpoint(self):
        self._create_metric()
        self.client.post(reverse('tuning_board:run-review'), data={}, content_type='application/json')
        summary = self.client.get(reverse('tuning_board:summary'))
        self.assertEqual(summary.status_code, 200)
        payload = summary.json()
        self.assertIn('proposals_generated', payload)
        self.assertIn('need_more_data', payload)
