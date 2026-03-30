from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.certification_board.models import CertificationLevel
from apps.certification_board.services.evidence import build_evidence_snapshot
from apps.certification_board.services.recommendation import generate_recommendation
from apps.chaos_lab.models import ChaosExperiment, ChaosRun, ResilienceBenchmark
from apps.champion_challenger.models import ChampionChallengerRun
from apps.champion_challenger.services.bindings import create_challenger_binding, get_or_create_champion_binding
from apps.evaluation_lab.models import EvaluationMetricSet, EvaluationRun
from apps.incident_commander.models import IncidentRecord
from apps.portfolio_governor.models import PortfolioGovernanceRun, PortfolioThrottleDecision
from apps.profile_manager.models import ProfileDecision, ProfileGovernanceRun
from apps.promotion_committee.models import PromotionReviewRun, StackEvidenceSnapshot
from apps.readiness_lab.models import ReadinessAssessmentRun, ReadinessProfile, ReadinessStatus
from apps.rollout_manager.models import StackRolloutPlan, StackRolloutRun
from apps.runtime_governor.models import RuntimeModeState
from apps.safety_guard.models import SafetyPolicyConfig


class CertificationBoardTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.champion = get_or_create_champion_binding()
        self.challenger = create_challenger_binding(name='cert-challenger', overrides={'execution_profile': 'balanced_paper'})
        self.profile = ReadinessProfile.objects.create(name='readiness', slug='readiness', config={})

    def _seed_baseline(self, readiness_status=ReadinessStatus.READY, chaos_score='72', open_critical=0, favorable='0.68', hard_stops=0):
        ReadinessAssessmentRun.objects.create(readiness_profile=self.profile, status=readiness_status, overall_score=Decimal('0.8'), summary='seed')

        evaluation = EvaluationRun.objects.create(status='READY', summary='eval')
        EvaluationMetricSet.objects.create(
            run=evaluation,
            favorable_review_rate=Decimal(favorable),
            block_rate=Decimal('0.12'),
            hard_stop_count=hard_stops,
            safety_events_count=0,
        )

        chaos_experiment = ChaosExperiment.objects.create(name='chaos', slug='chaos-cert', experiment_type='queue_pressure_spike', target_module='runtime')
        chaos_run = ChaosRun.objects.create(experiment=chaos_experiment, status='SUCCESS', started_at=evaluation.started_at, finished_at=evaluation.started_at)
        ResilienceBenchmark.objects.create(
            run=chaos_run,
            experiment=chaos_experiment,
            recovery_success_rate=Decimal('0.91'),
            resilience_score=Decimal(chaos_score),
        )

        ChampionChallengerRun.objects.create(
            champion_binding=self.champion,
            challenger_binding=self.challenger,
            status='COMPLETED',
            recommendation_code='CHALLENGER_PROMISING',
            markets_evaluated=20,
            summary='good',
        )

        evidence = StackEvidenceSnapshot.objects.create(champion_binding=self.champion, challenger_binding=self.challenger)
        PromotionReviewRun.objects.create(status='COMPLETED', evidence_snapshot=evidence, recommendation_code='KEEP_CURRENT_CHAMPION', confidence=Decimal('0.71'))

        plan = StackRolloutPlan.objects.create(champion_binding=self.champion, candidate_binding=self.challenger, mode='CANARY')
        StackRolloutRun.objects.create(plan=plan, status='COMPLETED')

        throttle = PortfolioThrottleDecision.objects.create(state='NORMAL', recommended_max_new_positions=3, recommended_max_size_multiplier=Decimal('1.2'))
        PortfolioGovernanceRun.objects.create(status='COMPLETED', throttle_decision=throttle)

        profile_run = ProfileGovernanceRun.objects.create(status='COMPLETED', regime='NORMAL', runtime_mode='PAPER_SEMI_AUTO')
        ProfileDecision.objects.create(
            run=profile_run,
            target_research_profile='research_balanced',
            target_signal_profile='signal_balanced',
            target_opportunity_supervisor_profile='opp_balanced',
            target_mission_control_profile='mission_balanced',
            target_portfolio_governor_profile='portfolio_balanced',
        )

        RuntimeModeState.objects.create(current_mode='PAPER_SEMI_AUTO', status='ACTIVE', set_by='manual')
        SafetyPolicyConfig.objects.update_or_create(name='default', defaults={'status': 'HEALTHY'})

        for idx in range(open_critical):
            IncidentRecord.objects.create(
                incident_type='runtime_conflict',
                severity='critical',
                status='OPEN',
                title=f'critical-{idx}',
                source_app='tests',
                first_seen_at=evaluation.started_at,
                last_seen_at=evaluation.started_at,
            )

    def test_evidence_snapshot_basic(self):
        self._seed_baseline()
        snapshot = build_evidence_snapshot()
        self.assertEqual(snapshot.readiness_summary.get('status'), 'READY')
        self.assertIn('latest_resilience_score', snapshot.chaos_benchmark_summary)

    def test_not_certified_by_critical_blockers(self):
        self._seed_baseline(readiness_status=ReadinessStatus.NOT_READY, chaos_score='35', open_critical=1)
        snapshot = build_evidence_snapshot()
        recommendation = generate_recommendation(snapshot)
        self.assertIn(recommendation.level, {CertificationLevel.NOT_CERTIFIED, CertificationLevel.REMEDIATION_REQUIRED})

    def test_defensive_certification_for_limited_evidence(self):
        self._seed_baseline(readiness_status=ReadinessStatus.CAUTION, favorable='0.57')
        snapshot = build_evidence_snapshot()
        recommendation = generate_recommendation(snapshot)
        self.assertEqual(recommendation.level, CertificationLevel.PAPER_CERTIFIED_DEFENSIVE)

    def test_remediation_recommendation(self):
        self._seed_baseline(readiness_status=ReadinessStatus.NOT_READY)
        response = self.client.post(reverse('certification_board:run-review'), {}, format='json')
        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload['recommendation_code'], 'REQUIRE_REMEDIATION')

    def test_current_certification_endpoint(self):
        self._seed_baseline()
        self.client.post(reverse('certification_board:run-review'), {}, format='json')
        response = self.client.get(reverse('certification_board:current'))
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.json()['current_certification'])

    def test_core_endpoints(self):
        self._seed_baseline()
        create_res = self.client.post(reverse('certification_board:run-review'), {'decision_mode': 'RECOMMENDATION_ONLY'}, format='json')
        self.assertEqual(create_res.status_code, 201)
        run_id = create_res.json()['id']

        runs_res = self.client.get(reverse('certification_board:runs'))
        self.assertEqual(runs_res.status_code, 200)
        detail_res = self.client.get(reverse('certification_board:run-detail', kwargs={'pk': run_id}))
        self.assertEqual(detail_res.status_code, 200)
        summary_res = self.client.get(reverse('certification_board:summary'))
        self.assertEqual(summary_res.status_code, 200)

    def test_post_rollout_review_and_summary_endpoints(self):
        response = self.client.post(reverse('certification_board:run-post-rollout-review'), {'actor': 'test'}, format='json')
        self.assertEqual(response.status_code, 201)
        summary = self.client.get(reverse('certification_board:post-rollout-summary'))
        self.assertEqual(summary.status_code, 200)
        self.assertIn('candidate_count', summary.json())
