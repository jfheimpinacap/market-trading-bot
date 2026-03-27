from rest_framework import serializers

from apps.venue_account.models import (
    VenueAccountSnapshot,
    VenueBalanceSnapshot,
    VenueOrderSnapshot,
    VenuePositionSnapshot,
    VenueReconciliationIssue,
    VenueReconciliationRun,
)


class VenueAccountSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = VenueAccountSnapshot
        fields = '__all__'


class VenueBalanceSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = VenueBalanceSnapshot
        fields = '__all__'


class VenueOrderSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = VenueOrderSnapshot
        fields = '__all__'


class VenuePositionSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = VenuePositionSnapshot
        fields = '__all__'


class VenueReconciliationIssueSerializer(serializers.ModelSerializer):
    class Meta:
        model = VenueReconciliationIssue
        fields = '__all__'


class VenueReconciliationRunSerializer(serializers.ModelSerializer):
    issues = VenueReconciliationIssueSerializer(read_only=True, many=True)

    class Meta:
        model = VenueReconciliationRun
        fields = '__all__'


class VenueReconciliationRequestSerializer(serializers.Serializer):
    metadata = serializers.DictField(required=False)
