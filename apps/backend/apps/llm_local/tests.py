from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.learning_memory.models import LearningMemoryEntry
from apps.llm_local.clients import OllamaChatClient, OllamaEmbeddingClient
from apps.llm_local.errors import LlmUnavailableError
from apps.markets.demo_data import seed_demo_markets
from apps.markets.models import Market
from apps.paper_trading.services.portfolio import ensure_demo_account
from apps.postmortem_demo.services import generate_trade_review
from apps.proposal_engine.services import generate_trade_proposal
from apps.paper_trading.services.execution import execute_paper_trade


class LlmStatusEndpointTests(TestCase):
    client_class = APIClient

    @override_settings(LLM_ENABLED=False)
    def test_status_reports_disabled(self):
        response = self.client.get(reverse('llm_local:status'))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload['enabled'])
        self.assertEqual(payload['status'], 'disabled')


class OllamaClientTests(TestCase):
    @override_settings(LLM_ENABLED=True, LLM_PROVIDER='ollama', OLLAMA_BASE_URL='http://localhost:11434', OLLAMA_CHAT_MODEL='demo-model')
    @patch('apps.llm_local.clients.ollama.OllamaChatClient._post_json')
    def test_chat_client_parses_structured_json(self, mock_post_json):
        mock_post_json.return_value = {'message': {'content': '{"thesis":"Long thesis body here enough chars","summary":"Long summary text enough chars","key_risks":["a"],"confidence_note":"confidence ok"}'}}

        payload = OllamaChatClient().chat_json(system_prompt='sys', user_prompt='usr', schema_hint='ProposalThesisResult')

        self.assertEqual(payload['summary'], 'Long summary text enough chars')

    @override_settings(LLM_ENABLED=False)
    def test_embedding_client_raises_when_disabled(self):
        with self.assertRaises(LlmUnavailableError):
            OllamaEmbeddingClient().embed_text('hello world')


class LlmTaskEndpointTests(TestCase):
    client_class = APIClient

    def setUp(self):
        seed_demo_markets()
        self.account, _ = ensure_demo_account()
        self.market = Market.objects.get(slug='will-candidate-a-win-the-2028-election')

        self.proposal = generate_trade_proposal(market=self.market, paper_account=self.account)
        trade = execute_paper_trade(market=self.market, trade_type='BUY', side='YES', quantity=Decimal('5.0'), account=self.account).trade
        self.review = generate_trade_review(trade, refresh_existing=True).review
        self.memory = LearningMemoryEntry.objects.create(
            memory_type='trade_pattern',
            source_type='demo',
            market=self.market,
            outcome='negative',
            summary='Sample learning summary from review.',
            rationale='Sample learning rationale with enough detail.',
        )

    @override_settings(LLM_ENABLED=True)
    @patch('apps.llm_local.services.proposal_text.OllamaChatClient.chat_json')
    def test_proposal_thesis_generation(self, mock_chat_json):
        mock_chat_json.return_value = {
            'thesis': 'This enriched thesis explains opportunity and constraints in detail.',
            'summary': 'This summary is concise but still detailed enough for auditors.',
            'key_risks': ['Liquidity drift', 'Headline uncertainty'],
            'confidence_note': 'Confidence is bounded by sparse actionable signals.',
        }

        response = self.client.post(reverse('llm_local:proposal-thesis'), {'proposal_id': self.proposal.id}, format='json')

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['proposal_id'], self.proposal.id)
        self.assertIn('key_risks', payload['result'])

    @override_settings(LLM_ENABLED=True)
    @patch('apps.llm_local.services.postmortem_text.OllamaChatClient.chat_json')
    def test_postmortem_summary_generation(self, mock_chat_json):
        mock_chat_json.return_value = {
            'enriched_summary': 'The trade underperformed because momentum reversed after entry and volume fell.',
            'lessons_learned': ['Confirm persistence before scaling.'],
            'action_items': ['Require stronger confirmation signal.'],
        }

        response = self.client.post(reverse('llm_local:postmortem-summary'), {'review_id': self.review.id}, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['review_id'], self.review.id)

    @override_settings(LLM_ENABLED=True)
    @patch('apps.llm_local.services.learning_text.OllamaChatClient.chat_json')
    def test_learning_note_generation(self, mock_chat_json):
        mock_chat_json.return_value = {
            'note_title': 'Protect downside during fading momentum',
            'note_body': 'Recent negative outcomes suggest reducing size when confirmation is weak and volatility rises.',
            'tags': ['risk', 'discipline'],
            'suggested_follow_up': 'Track next 10 similar setups before changing base rules.',
        }

        response = self.client.post(reverse('llm_local:learning-note'), {'memory_entry_id': self.memory.id}, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['memory_entry_id'], self.memory.id)

    @override_settings(LLM_ENABLED=False)
    @patch('apps.llm_local.services.proposal_text.OllamaChatClient.chat_json', side_effect=LlmUnavailableError('disabled'))
    def test_fallback_when_llm_unavailable(self, mock_chat_json):
        response = self.client.post(reverse('llm_local:proposal-thesis'), {'proposal_id': self.proposal.id}, format='json')

        self.assertEqual(response.status_code, 503)
        payload = response.json()
        self.assertTrue(payload['degraded'])

    @override_settings(LLM_ENABLED=True)
    @patch('apps.llm_local.services.embeddings.OllamaEmbeddingClient.embed_text')
    def test_embed_endpoint_with_mock(self, mock_embed_text):
        mock_embed_text.return_value = [0.1, 0.2, 0.3]

        response = self.client.post(reverse('llm_local:embed'), {'text': 'hello world'}, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['embedding'], [0.1, 0.2, 0.3])
