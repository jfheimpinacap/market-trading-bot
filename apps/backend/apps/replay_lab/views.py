from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.replay_lab.models import ReplayRun, ReplayStep
from apps.replay_lab.serializers import ReplayRunRequestSerializer, ReplayRunSerializer, ReplayStepSerializer
from apps.replay_lab.services import build_summary, run_replay


class ReplayRunView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = ReplayRunRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        result = run_replay(config=serializer.validated_data)
        code = status.HTTP_201_CREATED if result.run.status in {'SUCCESS', 'PARTIAL'} else status.HTTP_400_BAD_REQUEST
        return Response(ReplayRunSerializer(result.run).data, status=code)


class ReplayRunListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ReplayRunSerializer

    def get_queryset(self):
        return ReplayRun.objects.order_by('-created_at', '-id')[:50]


class ReplayRunDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ReplayRunSerializer
    queryset = ReplayRun.objects.order_by('-created_at', '-id')


class ReplaySummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(build_summary(), status=status.HTTP_200_OK)


class ReplayRunStepsView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ReplayStepSerializer

    def get_queryset(self):
        return ReplayStep.objects.filter(replay_run_id=self.kwargs['pk']).order_by('step_index')[:500]
