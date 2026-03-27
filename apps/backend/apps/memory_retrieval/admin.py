from django.contrib import admin

from apps.memory_retrieval.models import MemoryDocument, MemoryRetrievalRun, RetrievedPrecedent


@admin.register(MemoryDocument)
class MemoryDocumentAdmin(admin.ModelAdmin):
    list_display = ('id', 'document_type', 'source_app', 'source_object_id', 'embedded_at', 'created_at')
    list_filter = ('document_type', 'source_app')
    search_fields = ('title', 'text_content', 'source_object_id')


@admin.register(MemoryRetrievalRun)
class MemoryRetrievalRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'query_type', 'result_count', 'created_at')
    list_filter = ('query_type',)
    search_fields = ('query_text',)


@admin.register(RetrievedPrecedent)
class RetrievedPrecedentAdmin(admin.ModelAdmin):
    list_display = ('id', 'retrieval_run', 'memory_document', 'rank', 'similarity_score')
    list_filter = ('retrieval_run__query_type',)
