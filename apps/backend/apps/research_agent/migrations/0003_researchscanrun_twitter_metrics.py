from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('research_agent', '0002_reddit_social_fusion_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='researchscanrun',
            name='social_items_total',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='researchscanrun',
            name='twitter_items_created',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
