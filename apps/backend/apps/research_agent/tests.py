from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.markets.demo_data import seed_demo_markets
from apps.research_agent.models import NarrativeAnalysis, NarrativeSource
from apps.research_agent.services.scan import run_research_scan

RSS_PAYLOAD = {
    'feed': {'title': 'Demo Feed'},
    'entries': [
        {
            'title': 'Election poll shifts toward candidate A',
            'link': 'https://example.com/a',
            'id': 'item-a',
            'published': 'Wed, 25 Mar 2026 10:00:00 +0000',
            'summary': 'Candidate A improves odds in latest poll.',
        },
        {
            'title': 'Fed signals slower rate cuts',
            'link': 'https://example.com/fed',
            'id': 'item-b',
            'published': 'Wed, 25 Mar 2026 11:00:00 +0000',
            'summary': 'Macro narrative shifts risk sentiment.',
        },
    ],
}


class ResearchAgentTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        self.client = APIClient()
        self.source = NarrativeSource.objects.create(
            name='Demo RSS',
            slug='demo-rss',
            source_type='rss',
            feed_url='https://example.com/feed.xml',
            is_enabled=True,
        )

    @patch('apps.research_agent.services.ingest.fetch_rss')
    @patch('apps.research_agent.services.analyze.embed_text', return_value=[0.1, 0.2, 0.3])
    @patch('apps.research_agent.services.analyze.OllamaChatClient.chat_json')
    def test_ingest_dedupe_analyze_link_candidate_and_endpoints(self, chat_json_mock, _embed_mock, fetch_rss_mock):
        fetch_rss_mock.return_value = RSS_PAYLOAD
        chat_json_mock.return_value = {
            'summary': 'Narrative suggests improving momentum for a yes outcome in election markets.',
            'sentiment': 'bullish',
            'confidence': 0.81,
            'entities': ['candidate A', 'election'],
            'topics': ['election', 'polling'],
            'market_relevance_score': 0.77,
            'market_implication': 'Potential divergence versus stale probability.',
        }

        first_run = run_research_scan()
        second_run = run_research_scan()

        self.assertEqual(first_run.items_created, 2)
        self.assertGreaterEqual(second_run.items_deduplicated, 2)
        self.assertTrue(NarrativeAnalysis.objects.exists())

        sources_response = self.client.get(reverse('research_agent:source-list-create'))
        run_response = self.client.post(reverse('research_agent:run-ingest'), {'run_analysis': True}, format='json')
        items_response = self.client.get(reverse('research_agent:item-list'))
        candidates_response = self.client.get(reverse('research_agent:candidate-list'))
        summary_response = self.client.get(reverse('research_agent:summary'))

        self.assertEqual(sources_response.status_code, 200)
        self.assertEqual(run_response.status_code, 200)
        self.assertEqual(items_response.status_code, 200)
        self.assertEqual(candidates_response.status_code, 200)
        self.assertEqual(summary_response.status_code, 200)
        self.assertGreaterEqual(summary_response.json()['item_count'], 2)
