from rest_framework import generics

from .models import Event, Market, Provider
from .serializers import EventSerializer, MarketDetailSerializer, MarketSerializer, ProviderSerializer


class ProviderListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ProviderSerializer
    queryset = Provider.objects.order_by('name')


class EventListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = EventSerializer
    queryset = Event.objects.select_related('provider').order_by('provider__name', 'title')


class MarketListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = MarketSerializer
    queryset = Market.objects.select_related('provider', 'event').order_by('provider__name', 'title')


class MarketDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = MarketDetailSerializer
    queryset = Market.objects.select_related('provider', 'event').prefetch_related('rules')
