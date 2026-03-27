from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='MemoryDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('document_type', models.CharField(choices=[('learning_note', 'Learning note'), ('postmortem_conclusion', 'Postmortem conclusion'), ('postmortem_perspective', 'Postmortem perspective'), ('research_candidate_snapshot', 'Research candidate snapshot'), ('prediction_score_snapshot', 'Prediction score snapshot'), ('risk_assessment_snapshot', 'Risk assessment snapshot'), ('replay_summary', 'Replay summary'), ('experiment_result', 'Experiment result'), ('readiness_assessment', 'Readiness assessment'), ('lifecycle_decision', 'Lifecycle decision'), ('execution_impact_summary', 'Execution impact summary'), ('trade_review', 'Trade review')], max_length=48)),
                ('source_app', models.CharField(max_length=64)),
                ('source_object_id', models.CharField(max_length=128)),
                ('title', models.CharField(max_length=255)),
                ('text_content', models.TextField()),
                ('structured_summary', models.JSONField(blank=True, default=dict)),
                ('tags', models.JSONField(blank=True, default=list)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('embedding', models.JSONField(blank=True, default=list)),
                ('embedding_model', models.CharField(blank=True, max_length=96)),
                ('embedded_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={'ordering': ['-created_at', '-id']},
        ),
        migrations.CreateModel(
            name='MemoryRetrievalRun',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('query_text', models.TextField()),
                ('query_type', models.CharField(choices=[('research', 'Research'), ('prediction', 'Prediction'), ('risk', 'Risk'), ('postmortem', 'Postmortem'), ('lifecycle', 'Lifecycle'), ('manual', 'Manual')], default='manual', max_length=24)),
                ('context_metadata', models.JSONField(blank=True, default=dict)),
                ('result_count', models.PositiveIntegerField(default=0)),
                ('metadata', models.JSONField(blank=True, default=dict)),
            ],
            options={'ordering': ['-created_at', '-id']},
        ),
        migrations.CreateModel(
            name='RetrievedPrecedent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('similarity_score', models.FloatField(default=0)),
                ('rank', models.PositiveIntegerField(default=1)),
                ('short_reason', models.CharField(blank=True, max_length=255)),
                ('memory_document', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='retrieved_precedents', to='memory_retrieval.memorydocument')),
                ('retrieval_run', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='precedents', to='memory_retrieval.memoryretrievalrun')),
            ],
            options={'ordering': ['rank', 'id']},
        ),
        migrations.AddIndex(
            model_name='memorydocument',
            index=models.Index(fields=['document_type', '-created_at'], name='memory_retri_documen_fc2f4e_idx'),
        ),
        migrations.AddIndex(
            model_name='memorydocument',
            index=models.Index(fields=['source_app', '-created_at'], name='memory_retri_source__ed4479_idx'),
        ),
        migrations.AddConstraint(
            model_name='memorydocument',
            constraint=models.UniqueConstraint(fields=('source_app', 'source_object_id', 'document_type'), name='memory_doc_source_unique'),
        ),
        migrations.AddConstraint(
            model_name='retrievedprecedent',
            constraint=models.UniqueConstraint(fields=('retrieval_run', 'rank'), name='memory_precedent_rank_unique'),
        ),
    ]
