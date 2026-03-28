from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.autonomy_manager.models import AutonomyDomain, AutonomyStageRecommendation, AutonomyStageState, AutonomyStageTransition
from apps.autonomy_manager.serializers import (
    AutonomyApplyTransitionSerializer,
    AutonomyDomainSerializer,
    AutonomyRollbackTransitionSerializer,
    AutonomyRunReviewSerializer,
    AutonomyStageRecommendationSerializer,
    AutonomyStageStateSerializer,
    AutonomyStageTransitionSerializer,
)
from apps.autonomy_manager.services.domains import sync_domain_catalog
from apps.autonomy_manager.services.evidence import collect_domain_evidence, resolve_linked_policy_profiles
from apps.autonomy_manager.services.recommendation import create_recommendation
from apps.autonomy_manager.services.reporting import build_autonomy_summary
from apps.autonomy_manager.services.transitions import (
    apply_transition,
    create_transition_from_recommendation,
    resolve_transition_readiness,
    rollback_transition,
)


class AutonomyDomainsView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = AutonomyDomainSerializer

    def get_queryset(self):
        sync_domain_catalog()
        return AutonomyDomain.objects.select_related('envelope', 'stage_state').order_by('slug')


class AutonomyStageStatesView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = AutonomyStageStateSerializer

    def get_queryset(self):
        sync_domain_catalog()
        return AutonomyStageState.objects.select_related('domain').order_by('domain__slug')


class AutonomyRecommendationsView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = AutonomyStageRecommendationSerializer

    def get_queryset(self):
        sync_domain_catalog()
        recs = AutonomyStageRecommendation.objects.select_related('domain', 'state').prefetch_related('transitions').order_by('-created_at', '-id')
        limit = int(self.request.query_params.get('limit', '200'))
        return recs[:max(1, min(limit, 500))]


class AutonomyReviewRunView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = AutonomyRunReviewSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)

        sync_domain_catalog()
        generated_recommendations: list[AutonomyStageRecommendation] = []
        generated_transitions: list[AutonomyStageTransition] = []

        for state in AutonomyStageState.objects.select_related('domain').all().order_by('domain__slug'):
            evidence = collect_domain_evidence(state.domain)
            state.linked_policy_profiles = resolve_linked_policy_profiles(state.domain)
            state.linked_action_types = list(state.domain.action_types or [])
            state.save(update_fields=['linked_policy_profiles', 'linked_action_types', 'updated_at'])

            recommendation = create_recommendation(state=state, evidence=evidence)
            generated_recommendations.append(recommendation)
            transition = create_transition_from_recommendation(recommendation)
            if transition:
                generated_transitions.append(transition)

        payload = {
            'summary': build_autonomy_summary(),
            'recommendations_generated': len(generated_recommendations),
            'transitions_generated': len(generated_transitions),
            'recommendations': AutonomyStageRecommendationSerializer(generated_recommendations, many=True).data,
        }
        return Response(payload, status=status.HTTP_200_OK)


class AutonomyTransitionApplyView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, pk, *args, **kwargs):
        transition = get_object_or_404(AutonomyStageTransition.objects.select_related('approval_request', 'state', 'domain'), pk=pk)
        transition = resolve_transition_readiness(transition)
        serializer = AutonomyApplyTransitionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        try:
            updated = apply_transition(
                transition=transition,
                applied_by=serializer.validated_data.get('applied_by') or 'local-operator',
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(AutonomyStageTransitionSerializer(updated).data, status=status.HTTP_200_OK)


class AutonomyTransitionRollbackView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, pk, *args, **kwargs):
        transition = get_object_or_404(AutonomyStageTransition.objects.select_related('state', 'domain'), pk=pk)
        serializer = AutonomyRollbackTransitionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        try:
            updated = rollback_transition(
                transition=transition,
                rolled_back_by=serializer.validated_data.get('rolled_back_by') or 'local-operator',
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(AutonomyStageTransitionSerializer(updated).data, status=status.HTTP_200_OK)


class AutonomySummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        sync_domain_catalog()
        return Response(build_autonomy_summary(), status=status.HTTP_200_OK)
