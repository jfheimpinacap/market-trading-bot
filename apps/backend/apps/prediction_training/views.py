from django.db.models import Count
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.prediction_training.models import PredictionDatasetRun, PredictionModelArtifact, PredictionTrainingRun
from apps.prediction_training.serializers import (
    PredictionDatasetBuildRequestSerializer,
    PredictionDatasetRunSerializer,
    PredictionModelArtifactSerializer,
    PredictionTrainingRunRequestSerializer,
    PredictionTrainingRunSerializer,
)
from apps.prediction_training.services.dataset import build_prediction_dataset
from apps.prediction_training.services.registry import activate_model, get_active_model_artifact
from apps.prediction_training.services.training import run_training


class PredictionBuildDatasetView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = PredictionDatasetBuildRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        result = build_prediction_dataset(
            name=serializer.validated_data['name'] or 'default_dataset',
            horizon_hours=serializer.validated_data['horizon_hours'],
        )
        return Response(PredictionDatasetRunSerializer(result.dataset_run).data, status=status.HTTP_201_CREATED)


class PredictionTrainRunCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = PredictionTrainingRunRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)

        dataset_run = PredictionDatasetRun.objects.filter(id=serializer.validated_data['dataset_run_id']).first()
        if dataset_run is None:
            return Response({'detail': 'Dataset run not found.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            result = run_training(dataset_run=dataset_run, model_name=serializer.validated_data['model_name'])
            payload = PredictionTrainingRunSerializer(result.training_run).data
            payload['model_artifact'] = PredictionModelArtifactSerializer(result.model_artifact).data if result.model_artifact else None
            return Response(payload, status=status.HTTP_201_CREATED)
        except Exception as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class PredictionTrainRunListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PredictionTrainingRunSerializer

    def get_queryset(self):
        return PredictionTrainingRun.objects.select_related('dataset_run').order_by('-started_at', '-id')[:100]


class PredictionTrainRunDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PredictionTrainingRunSerializer
    queryset = PredictionTrainingRun.objects.select_related('dataset_run').order_by('-started_at', '-id')


class PredictionModelListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PredictionModelArtifactSerializer

    def get_queryset(self):
        return PredictionModelArtifact.objects.select_related('training_run', 'training_run__dataset_run').order_by('-created_at', '-id')[:100]


class PredictionModelActivateView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, pk, *args, **kwargs):
        artifact = PredictionModelArtifact.objects.filter(id=pk).first()
        if artifact is None:
            return Response({'detail': 'Model artifact not found.'}, status=status.HTTP_404_NOT_FOUND)
        activate_model(artifact=artifact)
        return Response(PredictionModelArtifactSerializer(artifact).data, status=status.HTTP_200_OK)


class PredictionActiveModelView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        artifact = get_active_model_artifact()
        if artifact is None:
            return Response({'active_model': None}, status=status.HTTP_200_OK)
        return Response({'active_model': PredictionModelArtifactSerializer(artifact).data}, status=status.HTTP_200_OK)


class PredictionTrainSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        dataset_latest = PredictionDatasetRun.objects.order_by('-created_at', '-id').first()
        active_model = get_active_model_artifact()
        run_counts = {
            item['status']: item['total']
            for item in PredictionTrainingRun.objects.values('status').annotate(total=Count('id'))
        }
        return Response(
            {
                'latest_dataset': PredictionDatasetRunSerializer(dataset_latest).data if dataset_latest else None,
                'active_model': PredictionModelArtifactSerializer(active_model).data if active_model else None,
                'training_runs_by_status': run_counts,
                'models_total': PredictionModelArtifact.objects.count(),
            },
            status=status.HTTP_200_OK,
        )
