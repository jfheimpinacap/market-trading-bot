from django.db.models import Count, Max, Prefetch
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Event, Market, MarketSnapshot, MarketStatus, Provider
from .serializers import (
    EventListSerializer,
    MarketDetailSerializer,
    MarketListSerializer,
    MarketSystemSummarySerializer,
    ProviderSerializer,
)


class ProviderListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ProviderSerializer

    def get_queryset(self):
        return Provider.objects.annotate(
            event_count=Count('events', distinct=True),
            market_count=Count('markets', distinct=True),
        ).order_by('name')


class EventListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = EventListSerializer

    def get_queryset(self):
        queryset = Event.objects.select_related('provider').annotate(
            market_count=Count('markets', distinct=True),
        )

        provider = self.request.query_params.get('provider')
        if provider:
            queryset = queryset.filter(provider__slug=provider)

        status_value = self.request.query_params.get('status')
        if status_value:
            queryset = queryset.filter(status=status_value)

        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__iexact=category)

        source_type = self.request.query_params.get('source_type')
        if source_type:
            queryset = queryset.filter(source_type=source_type)

        return queryset.order_by('provider__name', 'title')


class MarketListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = MarketListSerializer
    ordering_fields = (
        'title',
        'created_at',
        'resolution_time',
        'current_market_probability',
        'liquidity',
        'volume_24h',
    )
    default_ordering = ('provider__name', 'title')

    def get_queryset(self):
        queryset = Market.objects.select_related('provider', 'event').annotate(
            snapshot_count=Count('snapshots', distinct=True),
            latest_snapshot_at=Max('snapshots__captured_at'),
        )

        provider = self.request.query_params.get('provider')
        if provider:
            queryset = queryset.filter(provider__slug=provider)

        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__iexact=category)

        status_value = self.request.query_params.get('status')
        if status_value:
            queryset = queryset.filter(status=status_value)

        source_type = self.request.query_params.get('source_type')
        if source_type:
            queryset = queryset.filter(source_type=source_type)

        event_id = self.request.query_params.get('event')
        if event_id:
            queryset = queryset.filter(event_id=event_id)

        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            normalized = is_active.strip().lower()
            if normalized in {'true', '1', 'yes'}:
                queryset = queryset.filter(is_active=True)
            elif normalized in {'false', '0', 'no'}:
                queryset = queryset.filter(is_active=False)

        active = self.request.query_params.get('active')
        if active is not None:
            normalized = active.strip().lower()
            if normalized in {'true', '1', 'yes'}:
                queryset = queryset.filter(is_active=True)
            elif normalized in {'false', '0', 'no'}:
                queryset = queryset.filter(is_active=False)

        is_demo = self.request.query_params.get('is_demo')
        if is_demo is not None:
            normalized = is_demo.strip().lower()
            if normalized in {'true', '1', 'yes'}:
                queryset = queryset.filter(source_type='demo')
            elif normalized in {'false', '0', 'no'}:
                queryset = queryset.exclude(source_type='demo')

        is_real = self.request.query_params.get('is_real')
        if is_real is not None:
            normalized = is_real.strip().lower()
            if normalized in {'true', '1', 'yes'}:
                queryset = queryset.filter(source_type='real_read_only')
            elif normalized in {'false', '0', 'no'}:
                queryset = queryset.exclude(source_type='real_read_only')

        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(title__icontains=search)

        ordering = self.request.query_params.get('ordering')
        if ordering:
            requested_fields = [field.strip() for field in ordering.split(',') if field.strip()]
            valid_fields = []
            for field in requested_fields:
                raw_field = field[1:] if field.startswith('-') else field
                if raw_field in self.ordering_fields:
                    valid_fields.append(field)
            if valid_fields:
                return queryset.order_by(*valid_fields)

        return queryset.order_by(*self.default_ordering)


class MarketDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = MarketDetailSerializer

    def get_queryset(self):
        recent_snapshots = Prefetch(
            'snapshots',
            queryset=MarketSnapshot.objects.order_by('-captured_at', '-id')[:5],
            to_attr='recent_snapshots_cache',
        )
        return Market.objects.select_related('provider', 'event', 'event__provider').annotate(
            snapshot_count=Count('snapshots', distinct=True),
            latest_snapshot_at=Max('snapshots__captured_at'),
        ).prefetch_related('rules', recent_snapshots)


class MarketSystemSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        payload = {
            'total_providers': Provider.objects.count(),
            'total_events': Event.objects.count(),
            'total_markets': Market.objects.count(),
            'active_markets': Market.objects.filter(is_active=True).count(),
            'resolved_markets': Market.objects.filter(status=MarketStatus.RESOLVED).count(),
            'total_snapshots': MarketSnapshot.objects.count(),
        }
        serializer = MarketSystemSummarySerializer(payload)
        return Response(serializer.data)
