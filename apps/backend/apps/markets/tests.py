from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Event, EventStatus, Market, MarketRule, MarketSnapshot, MarketStatus, Provider


class MarketsModelTests(TestCase):
    def setUp(self):
        self.provider = Provider.objects.create(
            name='Kalshi',
            slug='kalshi',
            base_url='https://kalshi.com',
            api_base_url='https://api.elections.kalshi.com',
        )

    def test_create_provider(self):
        self.assertEqual(Provider.objects.count(), 1)
        self.assertEqual(str(self.provider), 'Kalshi')
        self.assertTrue(self.provider.is_active)

    def test_create_event(self):
        event = Event.objects.create(
            provider=self.provider,
            provider_event_id='event-001',
            title='US Presidential Election 2028',
            category='politics',
            status=EventStatus.OPEN,
        )

        self.assertEqual(event.slug, 'us-presidential-election-2028')
        self.assertEqual(str(event), 'kalshi: US Presidential Election 2028')

    def test_create_market(self):
        event = Event.objects.create(
            provider=self.provider,
            provider_event_id='event-002',
            title='US CPI Release - April 2027',
            status=EventStatus.UPCOMING,
        )

        market = Market.objects.create(
            provider=self.provider,
            event=event,
            provider_market_id='market-001',
            ticker='CPIAPR27',
            title='Will CPI print above 3.0% in April 2027?',
            category='economics',
            status=MarketStatus.OPEN,
            current_market_probability=Decimal('0.5725'),
        )

        self.assertEqual(market.slug, 'will-cpi-print-above-30-in-april-2027')
        self.assertEqual(market.event, event)
        self.assertEqual(str(market), 'kalshi: Will CPI print above 3.0% in April 2027?')

    def test_create_market_snapshot(self):
        market = Market.objects.create(
            provider=self.provider,
            provider_market_id='market-002',
            title='Will ETH trade above $5,000 on December 31, 2027?',
            status=MarketStatus.OPEN,
        )

        snapshot = MarketSnapshot.objects.create(
            market=market,
            captured_at=timezone.now(),
            market_probability=Decimal('0.4100'),
            yes_price=Decimal('41.0000'),
            no_price=Decimal('59.0000'),
            spread=Decimal('1.2500'),
            volume_24h=Decimal('12000.0000'),
        )

        self.assertEqual(snapshot.market, market)
        self.assertEqual(snapshot.market_probability, Decimal('0.4100'))


class MarketsApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.provider = Provider.objects.create(
            name='Polymarket',
            slug='polymarket',
            base_url='https://polymarket.com',
            api_base_url='https://api.polymarket.com',
        )
        self.event = Event.objects.create(
            provider=self.provider,
            provider_event_id='pm-event-001',
            title='US Recession in 2027',
            status=EventStatus.OPEN,
        )
        self.market = Market.objects.create(
            provider=self.provider,
            event=self.event,
            provider_market_id='pm-market-001',
            title='Will the US enter a recession in 2027?',
            status=MarketStatus.OPEN,
            current_market_probability=Decimal('0.3300'),
        )
        MarketRule.objects.create(
            market=self.market,
            rule_text='Provider resolution text placeholder.',
            resolution_criteria='Resolves yes if the NBER declares a recession in 2027.',
        )

    def test_provider_list_endpoint(self):
        response = self.client.get(reverse('markets:provider-list'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]['slug'], 'polymarket')

    def test_market_list_endpoint(self):
        response = self.client.get('/api/markets/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]['title'], 'Will the US enter a recession in 2027?')
        self.assertEqual(response.json()[0]['provider']['slug'], 'polymarket')

    def test_market_detail_endpoint_includes_rules(self):
        response = self.client.get(reverse('markets:market-detail', kwargs={'pk': self.market.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['id'], self.market.id)
        self.assertEqual(len(response.json()['rules']), 1)
