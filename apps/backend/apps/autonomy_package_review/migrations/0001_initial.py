from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('autonomy_package', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PackageReviewRun',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('candidate_count', models.PositiveIntegerField(default=0)),
                ('pending_count', models.PositiveIntegerField(default=0)),
                ('acknowledged_count', models.PositiveIntegerField(default=0)),
                ('adopted_count', models.PositiveIntegerField(default=0)),
                ('deferred_count', models.PositiveIntegerField(default=0)),
                ('rejected_count', models.PositiveIntegerField(default=0)),
                ('blocked_count', models.PositiveIntegerField(default=0)),
                ('closed_count', models.PositiveIntegerField(default=0)),
                ('recommendation_summary', models.JSONField(blank=True, default=dict)),
                ('metadata', models.JSONField(blank=True, default=dict)),
            ],
            options={'ordering': ['-created_at', '-id']},
        ),
        migrations.CreateModel(
            name='PackageResolution',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('resolution_status', models.CharField(choices=[('PENDING', 'Pending'), ('ACKNOWLEDGED', 'Acknowledged'), ('ADOPTED', 'Adopted'), ('DEFERRED', 'Deferred'), ('REJECTED', 'Rejected'), ('BLOCKED', 'Blocked'), ('CLOSED', 'Closed')], default='PENDING', max_length=24)),
                ('resolution_type', models.CharField(choices=[('ROADMAP_PACKAGE_ACKNOWLEDGED', 'Roadmap package acknowledged'), ('SCENARIO_PACKAGE_ACKNOWLEDGED', 'Scenario package acknowledged'), ('PROGRAM_PACKAGE_ACKNOWLEDGED', 'Program package acknowledged'), ('MANAGER_PACKAGE_ACKNOWLEDGED', 'Manager package acknowledged'), ('OPERATOR_PACKAGE_ACKNOWLEDGED', 'Operator package acknowledged'), ('MANUAL_REVIEW_REQUIRED', 'Manual review required')], default='MANUAL_REVIEW_REQUIRED', max_length=48)),
                ('rationale', models.CharField(max_length=255)),
                ('reason_codes', models.JSONField(blank=True, default=list)),
                ('blockers', models.JSONField(blank=True, default=list)),
                ('resolved_by', models.CharField(blank=True, max_length=120)),
                ('resolved_at', models.DateTimeField(blank=True, null=True)),
                ('linked_target_artifact', models.CharField(blank=True, max_length=255)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('governance_package', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='package_resolution', to='autonomy_package.governancepackage')),
            ],
            options={
                'ordering': ['-updated_at', '-id'],
                'indexes': [models.Index(fields=['governance_package', '-updated_at'], name='autonomy_pa_governa_7ac64d_idx'), models.Index(fields=['resolution_status', '-updated_at'], name='autonomy_pa_resolut_72dd4f_idx')],
            },
        ),
        migrations.CreateModel(
            name='PackageReviewRecommendation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('recommendation_type', models.CharField(choices=[('ACKNOWLEDGE_PACKAGE', 'Acknowledge package'), ('MARK_PACKAGE_ADOPTED', 'Mark package adopted'), ('MARK_PACKAGE_DEFERRED', 'Mark package deferred'), ('MARK_PACKAGE_REJECTED', 'Mark package rejected'), ('REQUIRE_MANUAL_PACKAGE_REVIEW', 'Require manual package review'), ('KEEP_PACKAGE_PENDING', 'Keep package pending'), ('REORDER_PACKAGE_REVIEW_PRIORITY', 'Reorder package review priority')], max_length=56)),
                ('rationale', models.CharField(max_length=255)),
                ('reason_codes', models.JSONField(blank=True, default=list)),
                ('confidence', models.DecimalField(decimal_places=4, default=0, max_digits=6)),
                ('blockers', models.JSONField(blank=True, default=list)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('governance_package', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='package_review_recommendations', to='autonomy_package.governancepackage')),
                ('review_run', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='recommendations', to='autonomy_package_review.packagereviewrun')),
            ],
            options={
                'ordering': ['-created_at', '-id'],
                'indexes': [models.Index(fields=['recommendation_type', '-created_at'], name='autonomy_pa_recomme_25fe59_idx')],
            },
        ),
    ]
