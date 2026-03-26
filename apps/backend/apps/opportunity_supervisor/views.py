from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.opportunity_supervisor.models import OpportunityCycleItem, OpportunityCycleRun
from apps.opportunity_supervisor.serializers import OpportunityCycleItemSerializer, OpportunityCycleRunSerializer, RunOpportunityCycleSerializer
from apps.opportunity_supervisor.services import build_summary, list_profiles, run_opportunity_cycle


class OpportunityRunCycleView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RunOpportunityCycleSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        cycle = run_opportunity_cycle(profile_slug=serializer.validated_data.get('profile_slug'))
        return Response(OpportunityCycleRunSerializer(cycle).data, status=status.HTTP_200_OK)


class OpportunityCycleListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = OpportunityCycleRunSerializer

    def get_queryset(self):
        return OpportunityCycleRun.objects.order_by('-started_at', '-id')[:100]


class OpportunityCycleDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = OpportunityCycleRunSerializer
    queryset = OpportunityCycleRun.objects.order_by('-started_at', '-id')


class OpportunityItemListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = OpportunityCycleItemSerializer

    def get_queryset(self):
        queryset = OpportunityCycleItem.objects.select_related('market', 'proposal', 'execution_plan').order_by('-created_at', '-id')
        run_id = self.request.query_params.get('run_id')
        if run_id and run_id.isdigit():
            queryset = queryset.filter(run_id=int(run_id))
        return queryset[:500]


class OpportunitySummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        payload = build_summary()
        payload['profiles'] = list_profiles()
        return Response(payload, status=status.HTTP_200_OK)
