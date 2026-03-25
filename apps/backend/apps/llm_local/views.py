from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.llm_local.errors import LlmLocalError
from apps.llm_local.serializers import (
    EmbedRequestSerializer,
    LearningNoteRequestSerializer,
    LlmStatusSerializer,
    PostmortemSummaryRequestSerializer,
    ProposalThesisRequestSerializer,
)
from apps.llm_local.services import (
    build_llm_status,
    embed_text,
    embed_text_batch,
    enrich_learning_note,
    enrich_postmortem_summary,
    enrich_proposal_thesis,
)


class LlmStatusView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        payload = build_llm_status()
        return Response(LlmStatusSerializer(payload).data, status=status.HTTP_200_OK)


class ProposalThesisView(APIView):
    def post(self, request):
        serializer = ProposalThesisRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)

        try:
            payload = enrich_proposal_thesis(serializer.validated_data)
        except ObjectDoesNotExist:
            return Response({'detail': 'Trade proposal not found.'}, status=status.HTTP_404_NOT_FOUND)
        except LlmLocalError as exc:
            return Response({'detail': str(exc), 'degraded': True}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response(payload, status=status.HTTP_200_OK)


class PostmortemSummaryView(APIView):
    def post(self, request):
        serializer = PostmortemSummaryRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)

        try:
            payload = enrich_postmortem_summary(serializer.validated_data)
        except ObjectDoesNotExist:
            return Response({'detail': 'Trade review not found.'}, status=status.HTTP_404_NOT_FOUND)
        except LlmLocalError as exc:
            return Response({'detail': str(exc), 'degraded': True}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response(payload, status=status.HTTP_200_OK)


class LearningNoteView(APIView):
    def post(self, request):
        serializer = LearningNoteRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)

        try:
            payload = enrich_learning_note(serializer.validated_data)
        except ObjectDoesNotExist:
            return Response({'detail': 'Learning memory entry not found.'}, status=status.HTTP_404_NOT_FOUND)
        except LlmLocalError as exc:
            return Response({'detail': str(exc), 'degraded': True}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response(payload, status=status.HTTP_200_OK)


class LlmEmbedView(APIView):
    def post(self, request):
        serializer = EmbedRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)

        try:
            if 'text' in serializer.validated_data:
                vector = embed_text(serializer.validated_data['text'])
                payload = {'embedding': vector}
            else:
                vectors = embed_text_batch(serializer.validated_data['texts'])
                payload = {'embeddings': vectors}
        except LlmLocalError as exc:
            return Response({'detail': str(exc), 'degraded': True}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response(payload, status=status.HTTP_200_OK)
