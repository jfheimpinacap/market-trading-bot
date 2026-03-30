from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.certification_board.models import (
    BaselineResponseCase,
    ResponseEvidencePack,
    DownstreamAcknowledgementStatus,
    ResponseLifecycleRecommendationType,
    ResponseRoutingActionType,
    ResponseReviewStageStatus,
    ResponseReviewStageType,
    ResponseCaseDownstreamStatus,
    BaselineResponseEvidenceStatus,
    BaselineResponseRecommendationType,
    BaselineResponseRoutingTarget,
    BaselineResponseType,
    BaselineHealthRecommendationType,
    BaselineHealthStatus,
    BaselineHealthStatusCode,
    CertificationLevel,
)
from apps.certification_board.services.baseline_response.candidate_building import determine_response_type
from apps.certification_board.services.baseline_response.evidence_pack import build_response_evidence_pack
from apps.certification_board.services.baseline_response.recommendation import build_response_recommendation
from apps.certification_board.services.baseline_response.routing import build_routing_decision
from apps.certification_board.services.baseline_response.run import run_baseline_response_review
from apps.certification_board.services.evidence import build_evidence_snapshot
from apps.certification_board.services.baseline_health.recommendation import build_baseline_health_recommendation
from apps.certification_board.services.baseline_health.run import run_baseline_health_review
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

    def test_baseline_confirmation_endpoints(self):
        run_response = self.client.post(reverse('certification_board:run-baseline-confirmation'), {'actor': 'test'}, format='json')
        self.assertEqual(run_response.status_code, 201)

        summary_response = self.client.get(reverse('certification_board:baseline-summary'))
        self.assertEqual(summary_response.status_code, 200)
        self.assertIn('ready_to_confirm_count', summary_response.json())

        candidates_response = self.client.get(reverse('certification_board:baseline-candidates'))
        self.assertEqual(candidates_response.status_code, 200)
        confirmations_response = self.client.get(reverse('certification_board:baseline-confirmations'))
        self.assertEqual(confirmations_response.status_code, 200)
        snapshots_response = self.client.get(reverse('certification_board:binding-snapshots'))
        self.assertEqual(snapshots_response.status_code, 200)
        recommendations_response = self.client.get(reverse('certification_board:baseline-recommendations'))
        self.assertEqual(recommendations_response.status_code, 200)


    def test_baseline_activation_endpoints(self):
        self.client.post(reverse('certification_board:run-post-rollout-review'), {'actor': 'test'}, format='json')
        self.client.post(reverse('certification_board:run-baseline-confirmation'), {'actor': 'test'}, format='json')
        candidate_res = self.client.get(reverse('certification_board:baseline-candidates'))
        self.assertEqual(candidate_res.status_code, 200)
        candidates = candidate_res.json()
        if not candidates:
            self.skipTest('No baseline candidates available in current seed.')

        first_decision_id = candidates[0]['linked_certification_decision']
        self.client.post(reverse('certification_board:confirm-baseline', kwargs={'decision_id': first_decision_id}), {'actor': 'test'}, format='json')

        run_res = self.client.post(reverse('certification_board:run-baseline-activation'), {'actor': 'test'}, format='json')
        self.assertEqual(run_res.status_code, 201)

        activation_candidates_res = self.client.get(reverse('certification_board:activation-candidates'))
        self.assertEqual(activation_candidates_res.status_code, 200)
        baseline_activations_res = self.client.get(reverse('certification_board:baseline-activations'))
        self.assertEqual(baseline_activations_res.status_code, 200)
        active_bindings_res = self.client.get(reverse('certification_board:active-bindings'))
        self.assertEqual(active_bindings_res.status_code, 200)
        recs_res = self.client.get(reverse('certification_board:activation-recommendations'))
        self.assertEqual(recs_res.status_code, 200)
        summary_res = self.client.get(reverse('certification_board:activation-summary'))
        self.assertEqual(summary_res.status_code, 200)
        self.assertIn('ready_to_activate_count', summary_res.json())

        confirmations = self.client.get(reverse('certification_board:baseline-confirmations')).json()
        self.assertGreaterEqual(len(confirmations), 1)
        activation_res = self.client.post(
            reverse('certification_board:activate-baseline', kwargs={'confirmation_id': confirmations[0]['id']}),
            {'actor': 'test'},
            format='json',
        )
        self.assertEqual(activation_res.status_code, 200)

    def _activate_one_baseline(self):
        self.client.post(reverse('certification_board:run-post-rollout-review'), {'actor': 'test'}, format='json')
        self.client.post(reverse('certification_board:run-baseline-confirmation'), {'actor': 'test'}, format='json')
        candidates = self.client.get(reverse('certification_board:baseline-candidates')).json()
        if not candidates:
            self.skipTest('No baseline candidates available in current seed.')
        self.client.post(
            reverse('certification_board:confirm-baseline', kwargs={'decision_id': candidates[0]['linked_certification_decision']}),
            {'actor': 'test'},
            format='json',
        )
        self.client.post(reverse('certification_board:run-baseline-activation'), {'actor': 'test'}, format='json')
        confirmations = self.client.get(reverse('certification_board:baseline-confirmations')).json()
        self.client.post(
            reverse('certification_board:activate-baseline', kwargs={'confirmation_id': confirmations[0]['id']}),
            {'actor': 'test'},
            format='json',
        )

    def test_baseline_health_run_and_summary_endpoints(self):
        self._seed_baseline()
        self._activate_one_baseline()
        run_response = self.client.post(reverse('certification_board:run-baseline-health-review'), {'actor': 'test'}, format='json')
        self.assertEqual(run_response.status_code, 201)
        summary_response = self.client.get(reverse('certification_board:health-summary'))
        self.assertEqual(summary_response.status_code, 200)
        self.assertIn('active_baselines_reviewed', summary_response.json())

    def test_baseline_health_collections_endpoints(self):
        self._seed_baseline()
        self._activate_one_baseline()
        self.client.post(reverse('certification_board:run-baseline-health-review'), {'actor': 'test'}, format='json')
        self.assertEqual(self.client.get(reverse('certification_board:health-candidates')).status_code, 200)
        self.assertEqual(self.client.get(reverse('certification_board:health-status')).status_code, 200)
        self.assertEqual(self.client.get(reverse('certification_board:health-signals')).status_code, 200)
        self.assertEqual(self.client.get(reverse('certification_board:health-recommendations')).status_code, 200)

    def test_baseline_health_status_progression(self):
        self._seed_baseline()
        self._activate_one_baseline()
        result = run_baseline_health_review(actor='test')
        self.assertGreaterEqual(len(result['candidates']), 1)
        statuses = list(BaselineHealthStatus.objects.all())
        self.assertTrue(
            any(
                status.health_status
                in {
                    BaselineHealthStatusCode.HEALTHY,
                    BaselineHealthStatusCode.UNDER_WATCH,
                    BaselineHealthStatusCode.DEGRADED,
                    BaselineHealthStatusCode.ROLLBACK_REVIEW_RECOMMENDED,
                }
                for status in statuses
            )
        )

    def test_baseline_health_recommendation_mapping(self):
        self._seed_baseline()
        self._activate_one_baseline()
        result = run_baseline_health_review(actor='test')
        self.assertGreaterEqual(len(result['statuses']), 1)
        status = result['statuses'][0]
        recommendation = build_baseline_health_recommendation(review_run=result['run'], status=status)
        self.assertIn(
            recommendation.recommendation_type,
            {
                BaselineHealthRecommendationType.KEEP_BASELINE_ACTIVE,
                BaselineHealthRecommendationType.OPEN_TUNING_REVIEW,
                BaselineHealthRecommendationType.PREPARE_ROLLBACK_REVIEW,
                BaselineHealthRecommendationType.KEEP_UNDER_WATCH,
                BaselineHealthRecommendationType.REQUIRE_REEVALUATION,
                BaselineHealthRecommendationType.REQUIRE_MANUAL_BASELINE_REVIEW,
            },
        )

    def test_response_candidate_building_from_health_status(self):
        self._seed_baseline()
        self._activate_one_baseline()
        health_result = run_baseline_health_review(actor='test')
        status = health_result['statuses'][0]
        response_type = determine_response_type(status)
        self.assertIn(
            response_type,
            {
                None,
                BaselineResponseType.KEEP_UNDER_WATCH,
                BaselineResponseType.OPEN_REEVALUATION,
                BaselineResponseType.OPEN_TUNING_REVIEW,
                BaselineResponseType.REQUIRE_MANUAL_BASELINE_REVIEW,
                BaselineResponseType.PREPARE_ROLLBACK_REVIEW,
                BaselineResponseType.REQUIRE_COMMITTEE_RECHECK,
            },
        )

    def test_response_evidence_pack_status_levels(self):
        self._seed_baseline()
        self._activate_one_baseline()
        response_result = run_baseline_response_review(actor='test')
        self.assertGreaterEqual(len(response_result['cases']), 1)
        evidence = response_result['evidence_packs'][0]
        self.assertIn(
            evidence.evidence_status,
            {
                BaselineResponseEvidenceStatus.STRONG,
                BaselineResponseEvidenceStatus.MIXED,
                BaselineResponseEvidenceStatus.WEAK,
                BaselineResponseEvidenceStatus.INSUFFICIENT,
            },
        )

    def test_response_routing_targets(self):
        self._seed_baseline()
        self._activate_one_baseline()
        response_result = run_baseline_response_review(actor='test')
        self.assertGreaterEqual(len(response_result['cases']), 1)
        decision = response_result['routing_decisions'][0]
        self.assertIn(
            decision.routing_target,
            {
                BaselineResponseRoutingTarget.MONITORING_ONLY,
                BaselineResponseRoutingTarget.EVALUATION_LAB,
                BaselineResponseRoutingTarget.TUNING_BOARD,
                BaselineResponseRoutingTarget.ROLLBACK_REVIEW,
                BaselineResponseRoutingTarget.CERTIFICATION_BOARD,
                BaselineResponseRoutingTarget.PROMOTION_COMMITTEE,
            },
        )

    def test_candidate_building_prefers_health_recommendation_override(self):
        self._seed_baseline()
        self._activate_one_baseline()
        health_run = run_baseline_health_review(actor='test')
        status = BaselineHealthStatus.objects.filter(linked_candidate__review_run=health_run).order_by('-id').first()
        self.assertIsNotNone(status)
        recommendation = build_baseline_health_recommendation(review_run=health_run, status=status)
        recommendation.recommendation_type = BaselineHealthRecommendationType.OPEN_TUNING_REVIEW
        recommendation.save(update_fields=['recommendation_type', 'updated_at'])

        response_result = run_baseline_response_review(actor='test')
        response_case = next(item for item in response_result['cases'] if item.linked_baseline_health_status_id == status.id)
        self.assertEqual(response_case.response_type, BaselineResponseType.OPEN_TUNING_REVIEW)

    def test_response_routing_target_mapping(self):
        self._seed_baseline()
        self._activate_one_baseline()
        response_result = run_baseline_response_review(actor='test')
        template_case = response_result['cases'][0]
        mapping = {
            BaselineResponseType.KEEP_UNDER_WATCH: BaselineResponseRoutingTarget.MONITORING_ONLY,
            BaselineResponseType.OPEN_REEVALUATION: BaselineResponseRoutingTarget.EVALUATION_LAB,
            BaselineResponseType.OPEN_TUNING_REVIEW: BaselineResponseRoutingTarget.TUNING_BOARD,
            BaselineResponseType.PREPARE_ROLLBACK_REVIEW: BaselineResponseRoutingTarget.ROLLBACK_REVIEW,
        }
        for response_type, expected_target in mapping.items():
            case = BaselineResponseCase.objects.create(
                review_run=template_case.review_run,
                linked_active_binding=template_case.linked_active_binding,
                linked_baseline_health_status=template_case.linked_baseline_health_status,
                linked_health_signals=list(template_case.linked_health_signals or []),
                target_component=template_case.target_component,
                target_scope=template_case.target_scope,
                response_type=response_type,
                priority_level=template_case.priority_level,
                case_status=template_case.case_status,
                rationale=template_case.rationale,
                reason_codes=list(template_case.reason_codes or []),
                blockers=[],
                metadata=dict(template_case.metadata or {}),
            )
            decision = build_routing_decision(response_case=case)
            self.assertEqual(decision.routing_target, expected_target)

    def test_response_recommendation_more_evidence(self):
        self._seed_baseline()
        self._activate_one_baseline()
        response_run_result = run_baseline_response_review(actor='test')
        case = response_run_result['cases'][0]
        case.metadata['sample_count'] = 1
        case.save(update_fields=['metadata', 'updated_at'])
        evidence = build_response_evidence_pack(response_case=case)
        recommendation = build_response_recommendation(
            review_run=response_run_result['run'],
            response_case=case,
            evidence_pack=evidence,
        )
        self.assertIn(
            recommendation.recommendation_type,
            {
                BaselineResponseRecommendationType.OPEN_TUNING_REVIEW,
                BaselineResponseRecommendationType.REQUIRE_MORE_EVIDENCE,
                BaselineResponseRecommendationType.PREPARE_ROLLBACK_REVIEW,
            },
        )

    def test_response_recommendation_type_with_strong_vs_insufficient_evidence(self):
        self._seed_baseline()
        self._activate_one_baseline()
        response_result = run_baseline_response_review(actor='test')
        case = response_result['cases'][0]

        strong = ResponseEvidencePack.objects.create(
            linked_response_case=BaselineResponseCase.objects.create(
                review_run=case.review_run,
                linked_active_binding=case.linked_active_binding,
                linked_baseline_health_status=case.linked_baseline_health_status,
                linked_health_signals=list(case.linked_health_signals or []),
                target_component=case.target_component,
                target_scope=case.target_scope,
                response_type=BaselineResponseType.OPEN_TUNING_REVIEW,
                priority_level=case.priority_level,
                case_status=case.case_status,
                rationale=case.rationale,
                reason_codes=list(case.reason_codes or []),
                blockers=[],
                metadata=dict(case.metadata or {}),
            ),
            summary='strong evidence',
            confidence_score=Decimal('0.9'),
            severity_score=Decimal('0.8'),
            urgency_score=Decimal('0.8'),
            evidence_status=BaselineResponseEvidenceStatus.STRONG,
        )
        strong_recommendation = build_response_recommendation(
            review_run=response_result['run'],
            response_case=strong.linked_response_case,
            evidence_pack=strong,
        )
        self.assertEqual(strong_recommendation.recommendation_type, BaselineResponseRecommendationType.OPEN_TUNING_REVIEW)

        weak_case = BaselineResponseCase.objects.create(
            review_run=case.review_run,
            linked_active_binding=case.linked_active_binding,
            linked_baseline_health_status=case.linked_baseline_health_status,
            linked_health_signals=list(case.linked_health_signals or []),
            target_component=case.target_component,
            target_scope=case.target_scope,
            response_type=BaselineResponseType.PREPARE_ROLLBACK_REVIEW,
            priority_level=case.priority_level,
            case_status=case.case_status,
            rationale=case.rationale,
            reason_codes=list(case.reason_codes or []),
            blockers=[],
            metadata=dict(case.metadata or {}),
        )
        weak_evidence = ResponseEvidencePack.objects.create(
            linked_response_case=weak_case,
            summary='insufficient evidence',
            confidence_score=Decimal('0.1'),
            severity_score=Decimal('0.1'),
            urgency_score=Decimal('0.1'),
            evidence_status=BaselineResponseEvidenceStatus.INSUFFICIENT,
        )
        weak_recommendation = build_response_recommendation(
            review_run=response_result['run'],
            response_case=weak_case,
            evidence_pack=weak_evidence,
        )
        self.assertEqual(weak_recommendation.recommendation_type, BaselineResponseRecommendationType.REQUIRE_MORE_EVIDENCE)

    def test_baseline_response_summary_endpoint(self):
        self._seed_baseline()
        self._activate_one_baseline()
        run_res = self.client.post(reverse('certification_board:run-baseline-response-review'), {'actor': 'test'}, format='json')
        self.assertEqual(run_res.status_code, 201)
        self.assertEqual(self.client.get(reverse('certification_board:response-cases')).status_code, 200)
        self.assertEqual(self.client.get(reverse('certification_board:response-evidence-packs')).status_code, 200)
        self.assertEqual(self.client.get(reverse('certification_board:response-routing-decisions')).status_code, 200)
        self.assertEqual(self.client.get(reverse('certification_board:response-recommendations')).status_code, 200)
        summary_res = self.client.get(reverse('certification_board:response-summary'))
        self.assertEqual(summary_res.status_code, 200)
        self.assertIn('open_response_cases', summary_res.json())

    def test_response_action_candidates_build_from_response_cases(self):
        self._seed_baseline()
        self._activate_one_baseline()
        self.client.post(reverse('certification_board:run-baseline-response-review'), {'actor': 'test'}, format='json')
        run_res = self.client.post(reverse('certification_board:run-baseline-response-actions'), {'actor': 'test'}, format='json')
        self.assertEqual(run_res.status_code, 201)
        candidates_res = self.client.get(reverse('certification_board:response-action-candidates'))
        self.assertEqual(candidates_res.status_code, 200)
        self.assertGreaterEqual(len(candidates_res.json()), 1)

    def test_require_routing_recheck_when_routing_is_blocked(self):
        self._seed_baseline()
        self._activate_one_baseline()
        self.client.post(reverse('certification_board:run-baseline-response-review'), {'actor': 'test'}, format='json')
        cases = self.client.get(reverse('certification_board:response-cases')).json()
        case_id = cases[0]['id']
        routing = self.client.get(reverse('certification_board:response-routing-decisions')).json()
        for item in routing:
            if item['linked_response_case'] == case_id:
                item['routing_status'] = 'BLOCKED'
        # force blocked routing for deterministic recommendation
        from apps.certification_board.models import ResponseRoutingDecision
        decision = ResponseRoutingDecision.objects.get(linked_response_case_id=case_id)
        decision.routing_status = 'BLOCKED'
        decision.save(update_fields=['routing_status', 'updated_at'])
        self.client.post(reverse('certification_board:run-baseline-response-actions'), {'actor': 'test'}, format='json')
        actions = self.client.get(reverse('certification_board:response-routing-actions')).json()
        self.assertIn(ResponseRoutingActionType.REQUIRE_ROUTING_RECHECK, {item['action_type'] for item in actions})

    def test_response_routing_actions_cover_core_targets(self):
        self._seed_baseline()
        self._activate_one_baseline()
        self.client.post(reverse('certification_board:run-baseline-response-review'), {'actor': 'test'}, format='json')
        self.client.post(reverse('certification_board:run-baseline-response-actions'), {'actor': 'test'}, format='json')
        actions = self.client.get(reverse('certification_board:response-routing-actions')).json()
        self.assertGreaterEqual(len(actions), 1)
        allowed = {
            'SEND_TO_EVALUATION_REVIEW',
            'SEND_TO_TUNING_REVIEW',
            'SEND_TO_ROLLBACK_REVIEW',
            'KEEP_IN_MONITORING',
            'REQUIRE_ROUTING_RECHECK',
        }
        self.assertTrue(any(item['action_type'] in allowed for item in actions))

    def test_update_response_tracking_statuses(self):
        self._seed_baseline()
        self._activate_one_baseline()
        self.client.post(reverse('certification_board:run-baseline-response-review'), {'actor': 'test'}, format='json')
        self.client.post(reverse('certification_board:run-baseline-response-actions'), {'actor': 'test'}, format='json')
        case_id = self.client.get(reverse('certification_board:response-cases')).json()[0]['id']
        for downstream_status in [
            ResponseCaseDownstreamStatus.SENT,
            ResponseCaseDownstreamStatus.UNDER_REVIEW,
            ResponseCaseDownstreamStatus.COMPLETED,
            ResponseCaseDownstreamStatus.CLOSED_NO_ACTION,
        ]:
            response = self.client.post(
                reverse('certification_board:update-response-tracking', kwargs={'case_id': case_id}),
                {'downstream_status': downstream_status, 'tracked_by': 'test'},
                format='json',
            )
            self.assertEqual(response.status_code, 200)

    def test_baseline_response_action_summary_endpoint(self):
        self._seed_baseline()
        self._activate_one_baseline()
        self.client.post(reverse('certification_board:run-baseline-response-review'), {'actor': 'test'}, format='json')
        self.client.post(reverse('certification_board:run-baseline-response-actions'), {'actor': 'test'}, format='json')
        summary_res = self.client.get(reverse('certification_board:response-action-summary'))
        self.assertEqual(summary_res.status_code, 200)
        self.assertIn('ready_to_route', summary_res.json())

    def test_response_action_detail_endpoints(self):
        self._seed_baseline()
        self._activate_one_baseline()
        self.client.post(reverse('certification_board:run-baseline-response-review'), {'actor': 'test'}, format='json')
        self.client.post(reverse('certification_board:run-baseline-response-actions'), {'actor': 'test'}, format='json')

        action_id = self.client.get(reverse('certification_board:response-routing-actions')).json()[0]['id']
        action_res = self.client.get(reverse('certification_board:response-routing-action-detail', kwargs={'pk': action_id}))
        self.assertEqual(action_res.status_code, 200)

        case_id = self.client.get(reverse('certification_board:response-cases')).json()[0]['id']
        self.client.post(
            reverse('certification_board:update-response-tracking', kwargs={'case_id': case_id}),
            {'downstream_status': ResponseCaseDownstreamStatus.SENT, 'tracked_by': 'test'},
            format='json',
        )
        tracking_id = self.client.get(reverse('certification_board:response-tracking-records')).json()[0]['id']
        tracking_res = self.client.get(reverse('certification_board:response-tracking-record-detail', kwargs={'pk': tracking_id}))
        self.assertEqual(tracking_res.status_code, 200)

    def test_close_response_case_endpoint(self):
        self._seed_baseline()
        self._activate_one_baseline()
        self.client.post(reverse('certification_board:run-baseline-response-review'), {'actor': 'test'}, format='json')
        self.client.post(reverse('certification_board:run-baseline-response-actions'), {'actor': 'test'}, format='json')

        case_id = self.client.get(reverse('certification_board:response-cases')).json()[0]['id']
        close_res = self.client.post(
            reverse('certification_board:close-response-case', kwargs={'case_id': case_id}),
            {'tracked_by': 'test', 'tracking_notes': 'manual closure'},
            format='json',
        )
        self.assertEqual(close_res.status_code, 200)

        case = BaselineResponseCase.objects.get(pk=case_id)
        self.assertEqual(case.case_status, 'CLOSED_NO_ACTION')

    def test_lifecycle_acknowledgement_flow_sent_to_accepted(self):
        self._seed_baseline()
        self._activate_one_baseline()
        self.client.post(reverse('certification_board:run-baseline-response-review'), {'actor': 'test'}, format='json')
        self.client.post(reverse('certification_board:run-baseline-response-actions'), {'actor': 'test'}, format='json')
        case_id = self.client.get(reverse('certification_board:response-cases')).json()[0]['id']
        self.client.post(reverse('certification_board:route-response-case', kwargs={'case_id': case_id}), {'routed_by': 'test'}, format='json')
        self.client.post(reverse('certification_board:run-baseline-response-lifecycle'), {'actor': 'test'}, format='json')
        first_ack = self.client.get(reverse('certification_board:downstream-acknowledgements')).json()[0]
        self.assertEqual(first_ack['acknowledgement_status'], DownstreamAcknowledgementStatus.SENT)

        self.client.post(
            reverse('certification_board:acknowledge-response-case', kwargs={'case_id': case_id}),
            {'acknowledgement_status': DownstreamAcknowledgementStatus.ACKNOWLEDGED, 'acknowledged_by': 'board-a'},
            format='json',
        )
        self.client.post(
            reverse('certification_board:acknowledge-response-case', kwargs={'case_id': case_id}),
            {'acknowledgement_status': DownstreamAcknowledgementStatus.ACCEPTED_FOR_REVIEW, 'acknowledged_by': 'board-a'},
            format='json',
        )
        ack = self.client.get(reverse('certification_board:downstream-acknowledgements')).json()[0]
        self.assertEqual(ack['acknowledgement_status'], DownstreamAcknowledgementStatus.ACCEPTED_FOR_REVIEW)

    def test_review_stage_and_outcome_variants(self):
        self._seed_baseline()
        self._activate_one_baseline()
        self.client.post(reverse('certification_board:run-baseline-response-review'), {'actor': 'test'}, format='json')
        self.client.post(reverse('certification_board:run-baseline-response-actions'), {'actor': 'test'}, format='json')
        case_id = self.client.get(reverse('certification_board:response-cases')).json()[0]['id']
        self.client.post(reverse('certification_board:route-response-case', kwargs={'case_id': case_id}), {'routed_by': 'test'}, format='json')
        self.client.post(
            reverse('certification_board:acknowledge-response-case', kwargs={'case_id': case_id}),
            {'acknowledgement_status': DownstreamAcknowledgementStatus.WAITING_MORE_EVIDENCE, 'acknowledged_by': 'board-a'},
            format='json',
        )
        for stage_type in [ResponseReviewStageType.EVIDENCE_COLLECTION, ResponseReviewStageType.BOARD_REVIEW, ResponseReviewStageType.DOWNSTREAM_RESOLUTION]:
            stage_res = self.client.post(
                reverse('certification_board:update-response-stage', kwargs={'case_id': case_id}),
                {'stage_type': stage_type, 'stage_status': ResponseReviewStageStatus.ACTIVE, 'stage_actor': 'board-a'},
                format='json',
            )
            self.assertEqual(stage_res.status_code, 200)

        outcome_res = self.client.post(
            reverse('certification_board:record-downstream-outcome', kwargs={'case_id': case_id}),
            {'outcome_type': 'WAITING_EVIDENCE', 'outcome_status': 'DEFERRED', 'outcome_rationale': 'Need more evidence'},
            format='json',
        )
        self.assertEqual(outcome_res.status_code, 200)
        self.assertEqual(outcome_res.json()['outcome_type'], 'WAITING_EVIDENCE')

        reject_res = self.client.post(
            reverse('certification_board:record-downstream-outcome', kwargs={'case_id': case_id}),
            {'outcome_type': 'REJECTED_BY_TARGET', 'outcome_status': 'CONFIRMED', 'outcome_rationale': 'Rejected by board'},
            format='json',
        )
        self.assertEqual(reject_res.status_code, 200)
        self.assertEqual(reject_res.json()['outcome_type'], 'REJECTED_BY_TARGET')

        resolved_res = self.client.post(
            reverse('certification_board:record-downstream-outcome', kwargs={'case_id': case_id}),
            {'outcome_type': 'RESOLVED_BY_TARGET', 'outcome_status': 'CONFIRMED', 'outcome_rationale': 'Resolved'},
            format='json',
        )
        self.assertEqual(resolved_res.status_code, 200)
        self.assertEqual(resolved_res.json()['outcome_type'], 'RESOLVED_BY_TARGET')

    def test_lifecycle_recommendations_and_summary_endpoint(self):
        self._seed_baseline()
        self._activate_one_baseline()
        self.client.post(reverse('certification_board:run-baseline-response-review'), {'actor': 'test'}, format='json')
        self.client.post(reverse('certification_board:run-baseline-response-actions'), {'actor': 'test'}, format='json')
        case_id = self.client.get(reverse('certification_board:response-cases')).json()[0]['id']
        self.client.post(reverse('certification_board:route-response-case', kwargs={'case_id': case_id}), {'routed_by': 'test'}, format='json')
        self.client.post(reverse('certification_board:run-baseline-response-lifecycle'), {'actor': 'test'}, format='json')
        recommendation_types = {item['recommendation_type'] for item in self.client.get(reverse('certification_board:response-lifecycle-recommendations')).json()}
        self.assertIn(ResponseLifecycleRecommendationType.REQUEST_ACKNOWLEDGEMENT_UPDATE, recommendation_types)

        self.client.post(
            reverse('certification_board:acknowledge-response-case', kwargs={'case_id': case_id}),
            {'acknowledgement_status': DownstreamAcknowledgementStatus.NO_RESPONSE, 'acknowledged_by': 'board-a'},
            format='json',
        )
        self.client.post(reverse('certification_board:run-baseline-response-lifecycle'), {'actor': 'test'}, format='json')
        recommendation_types = {item['recommendation_type'] for item in self.client.get(reverse('certification_board:response-lifecycle-recommendations')).json()}
        self.assertIn(ResponseLifecycleRecommendationType.ESCALATE_FOR_FOLLOWUP, recommendation_types)

        self.client.post(
            reverse('certification_board:record-downstream-outcome', kwargs={'case_id': case_id}),
            {'outcome_type': 'RESOLVED_BY_TARGET', 'outcome_status': 'CONFIRMED', 'outcome_rationale': 'ready for closure'},
            format='json',
        )
        self.client.post(reverse('certification_board:run-baseline-response-lifecycle'), {'actor': 'test'}, format='json')
        recommendation_types = {item['recommendation_type'] for item in self.client.get(reverse('certification_board:response-lifecycle-recommendations')).json()}
        self.assertIn(ResponseLifecycleRecommendationType.PREPARE_CASE_RESOLUTION, recommendation_types)

        summary_res = self.client.get(reverse('certification_board:response-lifecycle-summary'))
        self.assertEqual(summary_res.status_code, 200)
        self.assertIn('routed_cases', summary_res.json())
