from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.policy_tuning.models import PolicyTuningApplicationLog, PolicyTuningCandidate
from apps.policy_tuning.serializers import (
    ApplyPolicyTuningCandidateSerializer,
    CreatePolicyTuningCandidateSerializer,
    PolicyTuningApplicationLogSerializer,
    PolicyTuningCandidateSerializer,
    PolicyTuningReviewRequestSerializer,
)
from apps.policy_tuning.services import apply_candidate, build_policy_tuning_summary, create_candidate_from_recommendation, list_candidates, review_candidate
from apps.policy_tuning.services.changes import generate_change_set_diff


class PolicyTuningCreateCandidateView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = CreatePolicyTuningCandidateSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        candidate = create_candidate_from_recommendation(
            recommendation_id=serializer.validated_data['recommendation_id'],
            status=serializer.validated_data.get('status'),
        )
        payload = PolicyTuningCandidateSerializer(candidate).data
        payload['diff'] = generate_change_set_diff(candidate)
        return Response(payload, status=status.HTTP_201_CREATED)


class PolicyTuningCandidateListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PolicyTuningCandidateSerializer

    def get_queryset(self):
        return list_candidates()


class PolicyTuningCandidateDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PolicyTuningCandidateSerializer

    def get_queryset(self):
        return PolicyTuningCandidate.objects.select_related('recommendation', 'current_profile', 'current_rule').prefetch_related('reviews', 'application_logs')


class PolicyTuningReviewView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, pk, *args, **kwargs):
        candidate = get_object_or_404(PolicyTuningCandidate, pk=pk)
        serializer = PolicyTuningReviewRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        updated = review_candidate(
            candidate=candidate,
            decision=serializer.validated_data['decision'],
            reviewer_note=serializer.validated_data.get('reviewer_note', ''),
            metadata=serializer.validated_data.get('metadata', {}),
        )
        payload = PolicyTuningCandidateSerializer(updated).data
        payload['diff'] = generate_change_set_diff(updated)
        return Response(payload, status=status.HTTP_200_OK)


class PolicyTuningApplyView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, pk, *args, **kwargs):
        candidate = get_object_or_404(PolicyTuningCandidate, pk=pk)
        serializer = ApplyPolicyTuningCandidateSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        log = apply_candidate(
            candidate=candidate,
            note=serializer.validated_data.get('note', ''),
            metadata=serializer.validated_data.get('metadata', {}),
        )
        payload = {
            'candidate': PolicyTuningCandidateSerializer(candidate).data,
            'application_log': PolicyTuningApplicationLogSerializer(log).data,
        }
        return Response(payload, status=status.HTTP_200_OK)


class PolicyTuningApplicationLogListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PolicyTuningApplicationLogSerializer

    def get_queryset(self):
        return PolicyTuningApplicationLog.objects.select_related('candidate', 'applied_to_profile', 'applied_to_rule').order_by('-applied_at', '-id')[:200]


class PolicyTuningSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(build_policy_tuning_summary(), status=status.HTTP_200_OK)
