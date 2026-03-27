from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.learning_memory.models import LearningMemoryEntry
from apps.memory_retrieval.models import MemoryDocument, MemoryQueryType, MemoryRetrievalRun
from apps.memory_retrieval.services.indexing import run_indexing
from apps.memory_retrieval.services.precedents import build_precedent_summary
from apps.memory_retrieval.services.retrieval import retrieve_precedents


class MemoryRetrievalTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        LearningMemoryEntry.objects.create(
            memory_type='trade_pattern',
            source_type='demo',
            outcome='negative',
            summary='Over-sized trade during volatility spike',
            rationale='Sizing exceeded cautious limits and failed quickly.',
        )
        LearningMemoryEntry.objects.create(
            memory_type='market_pattern',
            source_type='demo',
            outcome='positive',
            summary='Patience after macro rumor avoided overtrading',
            rationale='Waited for confirmation before entering.',
        )

    @patch('apps.memory_retrieval.services.embeddings.embed_text', return_value=[1.0, 0.0, 0.0])
    def test_indexing_creates_memory_documents(self, _embed):
        payload = run_indexing(sources=['learning'])
        self.assertGreaterEqual(payload['documents_total'], 2)
        self.assertEqual(MemoryDocument.objects.count(), 2)

    @patch('apps.memory_retrieval.services.retrieval.embed_text', return_value=[1.0, 0.0, 0.0])
    def test_retrieval_records_run_and_precedents(self, _query_embed):
        MemoryDocument.objects.create(
            document_type='learning_note',
            source_app='learning_memory',
            source_object_id='1',
            title='Negative precedent',
            text_content='volatility spike with oversized position',
            tags=['negative', 'oversized'],
            structured_summary={'lesson': 'Reduce size in volatility spikes.'},
            embedding=[1.0, 0.0, 0.0],
            embedding_model='mock',
        )
        run = retrieve_precedents(query_text='oversized volatility risk', query_type=MemoryQueryType.RISK)
        self.assertEqual(run.result_count, 1)
        self.assertEqual(MemoryRetrievalRun.objects.count(), 1)
        self.assertEqual(run.precedents.count(), 1)

        summary = build_precedent_summary(run)
        self.assertEqual(summary['matches'], 1)
        self.assertGreaterEqual(len(summary['prior_caution_signals']), 1)

    @patch('apps.memory_retrieval.services.indexing.ensure_document_embedding')
    def test_memory_endpoints(self, _ensure):
        MemoryDocument.objects.create(
            document_type='learning_note',
            source_app='learning_memory',
            source_object_id='999',
            title='Seed doc',
            text_content='seed text',
            embedding=[1.0, 0.0],
            embedding_model='mock',
            tags=['negative'],
        )
        index_response = self.client.post(reverse('memory_retrieval:index'), {'sources': ['learning']}, format='json')
        self.assertEqual(index_response.status_code, 200)

        with patch('apps.memory_retrieval.services.retrieval.embed_text', return_value=[1.0, 0.0]):
            retrieve_response = self.client.post(
                reverse('memory_retrieval:retrieve'),
                {'query_text': 'seed', 'query_type': 'manual', 'limit': 3},
                format='json',
            )
        self.assertEqual(retrieve_response.status_code, 200)
        run_id = retrieve_response.json()['run']['id']

        self.assertEqual(self.client.get(reverse('memory_retrieval:documents')).status_code, 200)
        self.assertEqual(self.client.get(reverse('memory_retrieval:retrieval-runs')).status_code, 200)
        self.assertEqual(self.client.get(reverse('memory_retrieval:retrieval-run-detail', kwargs={'pk': run_id})).status_code, 200)
        self.assertEqual(self.client.get(reverse('memory_retrieval:summary')).status_code, 200)
        self.assertEqual(self.client.get(f"{reverse('memory_retrieval:precedent-summary')}?run_id={run_id}").status_code, 200)
