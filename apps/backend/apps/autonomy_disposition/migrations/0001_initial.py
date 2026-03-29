from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('approval_center', '0001_initial'),
        ('autonomy_campaign', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CampaignDisposition',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('disposition_type', models.CharField(choices=[('CLOSED', 'Closed'), ('ABORTED', 'Aborted'), ('RETIRED', 'Retired'), ('COMPLETED_RECORDED', 'Completed recorded'), ('KEPT_OPEN', 'Kept open')], max_length=32)),
                ('disposition_status', models.CharField(choices=[('PENDING_REVIEW', 'Pending review'), ('APPROVAL_REQUIRED', 'Approval required'), ('READY', 'Ready'), ('APPLIED', 'Applied'), ('BLOCKED', 'Blocked'), ('REJECTED', 'Rejected'), ('EXPIRED', 'Expired')], default='PENDING_REVIEW', max_length=24)),
                ('rationale', models.CharField(max_length=255)),
                ('reason_codes', models.JSONField(blank=True, default=list)),
                ('blockers', models.JSONField(blank=True, default=list)),
                ('requires_approval', models.BooleanField(default=False)),
                ('applied_by', models.CharField(blank=True, max_length=120)),
                ('applied_at', models.DateTimeField(blank=True, null=True)),
                ('campaign_state_before', models.CharField(blank=True, max_length=24)),
                ('campaign_state_after', models.CharField(blank=True, max_length=24)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('campaign', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dispositions', to='autonomy_campaign.autonomycampaign')),
                ('linked_approval_request', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='autonomy_dispositions', to='approval_center.approvalrequest')),
            ],
            options={'ordering': ['-created_at', '-id']},
        ),
        migrations.CreateModel(
            name='DispositionRun',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('candidate_count', models.PositiveIntegerField(default=0)),
                ('ready_to_close_count', models.PositiveIntegerField(default=0)),
                ('ready_to_abort_count', models.PositiveIntegerField(default=0)),
                ('ready_to_retire_count', models.PositiveIntegerField(default=0)),
                ('require_more_review_count', models.PositiveIntegerField(default=0)),
                ('keep_open_count', models.PositiveIntegerField(default=0)),
                ('approval_required_count', models.PositiveIntegerField(default=0)),
                ('recommendation_summary', models.JSONField(blank=True, default=dict)),
                ('metadata', models.JSONField(blank=True, default=dict)),
            ],
            options={'ordering': ['-created_at', '-id']},
        ),
        migrations.CreateModel(
            name='DispositionRecommendation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('recommendation_type', models.CharField(choices=[('CLOSE_CAMPAIGN', 'Close campaign'), ('ABORT_CAMPAIGN', 'Abort campaign'), ('RETIRE_CAMPAIGN', 'Retire campaign'), ('RECORD_COMPLETION', 'Record completion'), ('KEEP_CAMPAIGN_OPEN', 'Keep campaign open'), ('REQUIRE_APPROVAL_FOR_DISPOSITION', 'Require approval for disposition'), ('REORDER_DISPOSITION_PRIORITY', 'Reorder disposition priority')], max_length=48)),
                ('rationale', models.CharField(max_length=255)),
                ('reason_codes', models.JSONField(blank=True, default=list)),
                ('confidence', models.DecimalField(decimal_places=4, default=0, max_digits=6)),
                ('blockers', models.JSONField(blank=True, default=list)),
                ('impacted_domains', models.JSONField(blank=True, default=list)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('disposition_run', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='recommendations', to='autonomy_disposition.dispositionrun')),
                ('target_campaign', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='disposition_recommendations', to='autonomy_campaign.autonomycampaign')),
            ],
            options={'ordering': ['-created_at', '-id']},
        ),
        migrations.AddIndex(model_name='campaigndisposition', index=models.Index(fields=['campaign', '-created_at'], name='autonomy_dis_campaign_b4cf47_idx')),
        migrations.AddIndex(model_name='campaigndisposition', index=models.Index(fields=['disposition_status', '-created_at'], name='autonomy_dis_disposi_ee0d70_idx')),
        migrations.AddIndex(model_name='dispositionrecommendation', index=models.Index(fields=['recommendation_type', '-created_at'], name='autonomy_dis_recomme_e9ea27_idx')),
    ]
