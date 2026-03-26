from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('research_agent', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='researchcandidate',
            name='rss_narrative_contribution',
            field=models.DecimalField(decimal_places=4, default=0, max_digits=6),
        ),
        migrations.AddField(
            model_name='researchcandidate',
            name='social_narrative_contribution',
            field=models.DecimalField(decimal_places=4, default=0, max_digits=6),
        ),
        migrations.AddField(
            model_name='researchcandidate',
            name='source_mix',
            field=models.CharField(default='news_only', max_length=24),
        ),
        migrations.AddField(
            model_name='researchscanrun',
            name='analyses_degraded',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='researchscanrun',
            name='reddit_items_created',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='researchscanrun',
            name='rss_items_created',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='researchscanrun',
            name='source_errors',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
