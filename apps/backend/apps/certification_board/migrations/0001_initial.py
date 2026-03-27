from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='CertificationEvidenceSnapshot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('readiness_summary', models.JSONField(blank=True, default=dict)),
                ('execution_evaluation_summary', models.JSONField(blank=True, default=dict)),
                ('champion_challenger_summary', models.JSONField(blank=True, default=dict)),
                ('promotion_summary', models.JSONField(blank=True, default=dict)),
                ('rollout_summary', models.JSONField(blank=True, default=dict)),
                ('incident_summary', models.JSONField(blank=True, default=dict)),
                ('chaos_benchmark_summary', models.JSONField(blank=True, default=dict)),
                ('portfolio_governor_summary', models.JSONField(blank=True, default=dict)),
                ('profile_manager_summary', models.JSONField(blank=True, default=dict)),
                ('runtime_safety_summary', models.JSONField(blank=True, default=dict)),
                ('degraded_or_rollback_summary', models.JSONField(blank=True, default=dict)),
                ('metadata', models.JSONField(blank=True, default=dict)),
            ],
            options={'ordering': ['-created_at', '-id']},
        ),
        migrations.CreateModel(
            name='OperatingEnvelope',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('max_autonomy_mode_allowed', models.CharField(default='PAPER_ASSIST', max_length=32)),
                ('max_new_entries_per_cycle', models.PositiveIntegerField(default=1)),
                ('max_size_multiplier_allowed', models.DecimalField(decimal_places=4, default=1, max_digits=8)),
                ('auto_execution_allowed', models.BooleanField(default=False)),
                ('canary_rollout_allowed', models.BooleanField(default=False)),
                ('aggressive_profiles_disallowed', models.BooleanField(default=True)),
                ('defensive_profiles_only', models.BooleanField(default=True)),
                ('allowed_profiles', models.JSONField(blank=True, default=list)),
                ('constrained_modules', models.JSONField(blank=True, default=list)),
                ('notes', models.TextField(blank=True)),
                ('constraints', models.JSONField(blank=True, default=list)),
            ],
            options={'ordering': ['-created_at', '-id']},
        ),
        migrations.CreateModel(
            name='CertificationRun',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('status', models.CharField(choices=[('COMPLETED', 'Completed'), ('FAILED', 'Failed')], default='COMPLETED', max_length=16)),
                ('decision_mode', models.CharField(default='RECOMMENDATION_ONLY', max_length=24)),
                ('certification_level', models.CharField(choices=[('NOT_CERTIFIED', 'Not certified'), ('PAPER_CERTIFIED_DEFENSIVE', 'Paper certified (defensive)'), ('PAPER_CERTIFIED_BALANCED', 'Paper certified (balanced)'), ('PAPER_CERTIFIED_HIGH_AUTONOMY', 'Paper certified (high autonomy)'), ('RECERTIFICATION_REQUIRED', 'Recertification required'), ('REMEDIATION_REQUIRED', 'Remediation required')], default='NOT_CERTIFIED', max_length=48)),
                ('recommendation_code', models.CharField(choices=[('HOLD_CURRENT_CERTIFICATION', 'Hold current certification'), ('UPGRADE_PAPER_AUTONOMY', 'Upgrade paper autonomy'), ('DOWNGRADE_TO_DEFENSIVE', 'Downgrade to defensive'), ('REQUIRE_REMEDIATION', 'Require remediation'), ('REQUIRE_RECERTIFICATION', 'Require recertification'), ('MANUAL_REVIEW_REQUIRED', 'Manual review required')], max_length=40)),
                ('confidence', models.DecimalField(decimal_places=4, default=0, max_digits=6)),
                ('rationale', models.TextField(blank=True)),
                ('reason_codes', models.JSONField(blank=True, default=list)),
                ('blocking_constraints', models.JSONField(blank=True, default=list)),
                ('remediation_items', models.JSONField(blank=True, default=list)),
                ('evidence_summary', models.JSONField(blank=True, default=dict)),
                ('summary', models.CharField(blank=True, max_length=255)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('evidence_snapshot', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='certification_runs', to='certification_board.certificationevidencesnapshot')),
                ('operating_envelope', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='certification_runs', to='certification_board.operatingenvelope')),
            ],
            options={'ordering': ['-created_at', '-id']},
        ),
        migrations.CreateModel(
            name='CertificationDecisionLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('event_type', models.CharField(default='RECOMMENDATION_ISSUED', max_length=32)),
                ('actor', models.CharField(default='certification_board', max_length=64)),
                ('notes', models.TextField(blank=True)),
                ('payload', models.JSONField(blank=True, default=dict)),
                ('run', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='decision_logs', to='certification_board.certificationrun')),
            ],
            options={'ordering': ['-created_at', '-id']},
        ),
    ]
