from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('memory_retrieval', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AgentPrecedentUse',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('agent_name', models.CharField(max_length=64)),
                ('source_app', models.CharField(max_length=64)),
                ('source_object_id', models.CharField(max_length=128)),
                ('precedent_count', models.PositiveIntegerField(default=0)),
                (
                    'influence_mode',
                    models.CharField(
                        choices=[
                            ('context_only', 'Context only'),
                            ('caution_boost', 'Caution boost'),
                            ('confidence_adjust', 'Confidence adjust'),
                            ('rationale_only', 'Rationale only'),
                        ],
                        default='context_only',
                        max_length=32,
                    ),
                ),
                ('metadata', models.JSONField(blank=True, default=dict)),
                (
                    'retrieval_run',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='agent_uses',
                        to='memory_retrieval.memoryretrievalrun',
                    ),
                ),
            ],
            options={
                'ordering': ['-created_at', '-id'],
            },
        ),
        migrations.AddIndex(
            model_name='agentprecedentuse',
            index=models.Index(fields=['agent_name', '-created_at'], name='memory_retr_agent_n_94019c_idx'),
        ),
        migrations.AddIndex(
            model_name='agentprecedentuse',
            index=models.Index(fields=['source_app', '-created_at'], name='memory_retr_source__c6a156_idx'),
        ),
    ]
