from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.autonomy_campaign.models import AutonomyCampaign
<<<<<<< HEAD
from apps.autonomy_intervention.models import CampaignInterventionAction, CampaignInterventionRequest
=======
from apps.autonomy_intervention.models import CampaignInterventionAction, CampaignInterventionRequest, InterventionSourceType
>>>>>>> origin/main
from apps.autonomy_intervention.serializers import (
    CampaignInterventionActionSerializer,
    CampaignInterventionRequestSerializer,
    CreateInterventionRequestSerializer,
<<<<<<< HEAD
    ExecuteInterventionRequestSerializer,
    RunInterventionReviewSerializer,
)
from apps.autonomy_intervention.services import build_intervention_summary, create_request, execute_request, run_intervention_review


class AutonomyInterventionRequestsView(APIView):
=======
    ExecuteInterventionSerializer,
    RunReviewSerializer,
)
from apps.autonomy_intervention.services import (
    build_summary_payload,
    create_intervention_request,
    execute_request,
    generate_intervention_summary,
    map_recommendation_to_action,
)
from apps.autonomy_operations.models import CampaignAttentionSignal, OperationsRecommendation


class InterventionRequestsView(APIView):
>>>>>>> origin/main
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
<<<<<<< HEAD
        rows = CampaignInterventionRequest.objects.select_related('campaign', 'approval_request').order_by('-created_at', '-id')[:200]
        return Response(CampaignInterventionRequestSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomyInterventionRequestDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, request_id: int, *args, **kwargs):
        row = get_object_or_404(CampaignInterventionRequest.objects.select_related('campaign', 'approval_request'), pk=request_id)
        return Response(CampaignInterventionRequestSerializer(row).data, status=status.HTTP_200_OK)


class AutonomyInterventionActionsView(APIView):
=======
        rows = CampaignInterventionRequest.objects.select_related('campaign', 'linked_signal', 'linked_recommendation', 'approval_request').order_by('-created_at', '-id')[:200]
        return Response(CampaignInterventionRequestSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class InterventionActionsView(APIView):
>>>>>>> origin/main
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = CampaignInterventionAction.objects.select_related('campaign', 'intervention_request').order_by('-created_at', '-id')[:200]
        return Response(CampaignInterventionActionSerializer(rows, many=True).data, status=status.HTTP_200_OK)


<<<<<<< HEAD
class AutonomyInterventionSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(build_intervention_summary(), status=status.HTTP_200_OK)


class AutonomyInterventionRunReviewView(APIView):
=======
class InterventionRunReviewView(APIView):
>>>>>>> origin/main
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
<<<<<<< HEAD
        serializer = RunInterventionReviewSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        result = run_intervention_review(actor=serializer.validated_data.get('actor') or 'operator-ui')
        return Response(
            {
                'run_id': result['run'].id,
                'created_request_count': len(result['created_requests']),
                'created_request_ids': [row.id for row in result['created_requests']],
            },
            status=status.HTTP_200_OK,
        )


class AutonomyInterventionCreateRequestView(APIView):
=======
        serializer = RunReviewSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        actor = serializer.validated_data['actor']

        created = 0
        recommendations = OperationsRecommendation.objects.select_related('target_campaign').order_by('-created_at', '-id')[:100]
        for rec in recommendations:
            if not rec.target_campaign_id:
                continue
            requested_action = map_recommendation_to_action(rec.recommendation_type)
            if not requested_action:
                continue
            exists = CampaignInterventionRequest.objects.filter(
                campaign_id=rec.target_campaign_id,
                linked_recommendation=rec,
                request_status__in=['OPEN', 'APPROVAL_REQUIRED', 'READY'],
            ).exists()
            if exists:
                continue
            create_intervention_request(
                campaign=rec.target_campaign,
                source_type=InterventionSourceType.OPERATIONS_RECOMMENDATION,
                requested_action=requested_action,
                severity='HIGH' if rec.recommendation_type in {'PAUSE_CAMPAIGN', 'REVIEW_FOR_ABORT'} else 'MEDIUM',
                rationale=rec.rationale,
                reason_codes=rec.reason_codes,
                blockers=rec.blockers,
                linked_recommendation=rec,
                requested_by=actor,
                metadata={'run_review': True},
                approval_required=requested_action in {'ESCALATE_TO_APPROVAL', 'REVIEW_FOR_ABORT'},
            )
            created += 1

        run = generate_intervention_summary(actor=actor)
        return Response({'run': run.id, 'created_requests': created}, status=status.HTTP_200_OK)


class InterventionSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(build_summary_payload(), status=status.HTTP_200_OK)


class InterventionCreateRequestView(APIView):
>>>>>>> origin/main
    authentication_classes = []
    permission_classes = []

    def post(self, request, campaign_id: int, *args, **kwargs):
<<<<<<< HEAD
        serializer = CreateInterventionRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        campaign = get_object_or_404(AutonomyCampaign, pk=campaign_id)
        row = create_request(campaign=campaign, **serializer.validated_data)
        return Response(CampaignInterventionRequestSerializer(row).data, status=status.HTTP_201_CREATED)


class AutonomyInterventionExecuteRequestView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, request_id: int, *args, **kwargs):
        serializer = ExecuteInterventionRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        row = get_object_or_404(CampaignInterventionRequest, pk=request_id)
        action = execute_request(
            request=row,
            actor=serializer.validated_data.get('actor') or 'operator-ui',
            rationale=serializer.validated_data.get('rationale') or 'Manual intervention execution',
            metadata=serializer.validated_data.get('metadata') or {},
        )
        return Response(CampaignInterventionActionSerializer(action).data, status=status.HTTP_200_OK)


class AutonomyInterventionCancelRequestView(APIView):
=======
        campaign = get_object_or_404(AutonomyCampaign, pk=campaign_id)
        serializer = CreateInterventionRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        linked_signal = CampaignAttentionSignal.objects.filter(pk=data.get('linked_signal_id')).first() if data.get('linked_signal_id') else None
        linked_recommendation = OperationsRecommendation.objects.filter(pk=data.get('linked_recommendation_id')).first() if data.get('linked_recommendation_id') else None
        intervention = create_intervention_request(
            campaign=campaign,
            source_type=data.get('source_type') or InterventionSourceType.MANUAL,
            requested_action=data['requested_action'],
            severity=data.get('severity') or 'MEDIUM',
            rationale=data.get('rationale') or '',
            reason_codes=data.get('reason_codes') or [],
            blockers=data.get('blockers') or [],
            linked_signal=linked_signal,
            linked_recommendation=linked_recommendation,
            requested_by=data.get('requested_by') or 'operator-ui',
            metadata=data.get('metadata') or {},
            approval_required=data['requested_action'] in {'ESCALATE_TO_APPROVAL', 'REVIEW_FOR_ABORT'},
        )
        return Response(CampaignInterventionRequestSerializer(intervention).data, status=status.HTTP_201_CREATED)


class InterventionExecuteRequestView(APIView):
>>>>>>> origin/main
    authentication_classes = []
    permission_classes = []

    def post(self, request, request_id: int, *args, **kwargs):
<<<<<<< HEAD
        row = get_object_or_404(CampaignInterventionRequest, pk=request_id)
        if row.request_status not in {'OPEN', 'READY', 'APPROVAL_REQUIRED', 'BLOCKED'}:
            return Response({'detail': 'Request cannot be cancelled in current state.'}, status=status.HTTP_400_BAD_REQUEST)
        row.request_status = 'EXPIRED'
        row.save(update_fields=['request_status', 'updated_at'])
        return Response(CampaignInterventionRequestSerializer(row).data, status=status.HTTP_200_OK)
=======
        intervention_request = get_object_or_404(CampaignInterventionRequest, pk=request_id)
        serializer = ExecuteInterventionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        action = execute_request(request=intervention_request, actor=serializer.validated_data['actor'])
        return Response(CampaignInterventionActionSerializer(action).data, status=status.HTTP_200_OK)
>>>>>>> origin/main
