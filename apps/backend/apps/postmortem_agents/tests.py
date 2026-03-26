from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.agents.models import AgentHandoff, AgentPipelineRun, AgentRun
from apps.markets.demo_data import seed_demo_markets
from apps.markets.models import Market
from apps.paper_trading.models import PaperAccount, PaperTrade, PaperTradeType
from apps.postmortem_agents.models import PostmortemAgentReview, PostmortemBoardConclusion, PostmortemBoardRun
from apps.postmortem_demo.services.review import generate_trade_review
from apps.prediction_agent.services.scoring import score_market_prediction
from apps.research_agent.models import ResearchCandidate
from apps.risk_agent.services.assessment import run_risk_assessment
from apps.risk_agent.services.sizing import run_risk_sizing


class PostmortemBoardApiTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        self.client = APIClient()
        market = Market.objects.filter(is_active=True).order_by('id').first()
        self.assertIsNotNone(market)
        self.market = market
        self.account = PaperAccount.objects.create(name='Board Test', slug='board-test', initial_balance=Decimal('20000.00'), cash_balance=Decimal('20000.00'), equity=Decimal('20000.00'))
        self.trade = PaperTrade.objects.create(
            account=self.account,
            market=self.market,
            trade_type=PaperTradeType.BUY,
            side='YES',
            quantity=Decimal('4.0000'),
            price=Decimal('47.0000'),
            gross_amount=Decimal('188.00'),
            fees=Decimal('1.00'),
            status='EXECUTED',
            metadata={},
        )
        self.review = generate_trade_review(self.trade, refresh_existing=True).review

        ResearchCandidate.objects.get_or_create(
            market=self.market,
            defaults={'short_thesis': 'Divergence candidate', 'priority': '90.00'},
        )
        score = score_market_prediction(market=self.market, triggered_by='test').score
        assessment = run_risk_assessment(market=self.market, prediction_score=score)
        run_risk_sizing(risk_assessment=assessment, base_quantity=Decimal('3.0000'))

    def test_board_run_generates_reviews_and_conclusion(self):
        response = self.client.post(
            reverse('postmortem_agents:run'),
            {'related_trade_review_id': self.review.id, 'force_learning_rebuild': True},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn(payload['status'], ['SUCCESS', 'PARTIAL'])

        board_run = PostmortemBoardRun.objects.get(id=payload['id'])
        self.assertEqual(board_run.related_trade_review_id, self.review.id)
        self.assertEqual(board_run.perspective_reviews.count(), 5)
        self.assertTrue(PostmortemBoardConclusion.objects.filter(board_run=board_run).exists())

    def test_endpoints_return_board_state(self):
        self.client.post(reverse('postmortem_agents:run'), {'related_trade_review_id': self.review.id}, format='json')

        runs_response = self.client.get(reverse('postmortem_agents:runs'))
        summary_response = self.client.get(reverse('postmortem_agents:summary'))
        conclusions_response = self.client.get(reverse('postmortem_agents:conclusions'))
        reviews_response = self.client.get(reverse('postmortem_agents:reviews'))

        self.assertEqual(runs_response.status_code, 200)
        self.assertEqual(summary_response.status_code, 200)
        self.assertEqual(conclusions_response.status_code, 200)
        self.assertEqual(reviews_response.status_code, 200)
        self.assertGreaterEqual(len(runs_response.json()), 1)
        self.assertGreaterEqual(summary_response.json()['total_runs'], 1)

    def test_agents_pipeline_postmortem_board_cycle(self):
        response = self.client.post(
            reverse('agents:run-pipeline'),
            {
                'pipeline_type': 'postmortem_board_cycle',
                'triggered_from': 'manual',
                'payload': {'related_trade_review_id': self.review.id, 'force_learning_rebuild': False},
            },
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(AgentPipelineRun.objects.count(), 1)
        self.assertGreaterEqual(AgentRun.objects.count(), 2)
        self.assertGreaterEqual(AgentHandoff.objects.count(), 1)
        self.assertGreaterEqual(PostmortemAgentReview.objects.count(), 5)
