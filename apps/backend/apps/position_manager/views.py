from django.db.models import Count
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.position_manager.models import PositionLifecycleDecision, PositionLifecycleRun
from apps.position_manager.serializers import PositionLifecycleDecisionSerializer, PositionLifecycleRunSerializer, RunLifecycleRequestSerializer
from apps.position_manager.services import list_profiles


class RunPositionLifecycleView(generics.GenericAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = RunLifecycleRequestSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        run = serializer.save()
        return Response({'lifecycle_run': PositionLifecycleRunSerializer(run).data}, status=status.HTTP_201_CREATED)


class PositionLifecycleRunListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PositionLifecycleRunSerializer

    def get_queryset(self):
        return PositionLifecycleRun.objects.prefetch_related('decisions', 'decisions__exit_plan').order_by('-created_at', '-id')[:60]


class PositionLifecycleRunDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PositionLifecycleRunSerializer
    queryset = PositionLifecycleRun.objects.prefetch_related('decisions', 'decisions__exit_plan').order_by('-created_at', '-id')


class PositionLifecycleDecisionListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PositionLifecycleDecisionSerializer

    def get_queryset(self):
        return PositionLifecycleDecision.objects.select_related('paper_position', 'paper_position__market', 'exit_plan', 'run').order_by('-created_at', '-id')[:250]


class PositionLifecycleSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        latest = PositionLifecycleRun.objects.order_by('-created_at', '-id').first()
        status_counts = list(PositionLifecycleDecision.objects.values('status').annotate(count=Count('id')).order_by('status'))
        return Response(
            {
                'total_runs': PositionLifecycleRun.objects.count(),
                'total_decisions': PositionLifecycleDecision.objects.count(),
                'status_counts': status_counts,
                'latest_run': PositionLifecycleRunSerializer(latest).data if latest else None,
                'profiles': list_profiles(),
                'paper_demo_only': True,
                'real_execution_enabled': False,
            },
            status=status.HTTP_200_OK,
        )
