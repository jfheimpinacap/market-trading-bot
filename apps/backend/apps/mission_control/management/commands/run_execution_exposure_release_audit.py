from __future__ import annotations

import json

from django.core.management.base import BaseCommand

from apps.mission_control.services.execution_exposure_release_audit import build_execution_exposure_release_audit_snapshot


class Command(BaseCommand):
    help = 'Run execution exposure release audit diagnostics without changing policy or releasing entries.'

    def add_arguments(self, parser):
        parser.add_argument('--preset', type=str, default='live_read_only_paper_conservative')
        parser.add_argument('--window-minutes', type=int, default=60)
        parser.add_argument('--json', action='store_true', help='Emit JSON payload.')

    def handle(self, *args, **options):
        payload = build_execution_exposure_release_audit_snapshot(
            window_minutes=max(5, int(options.get('window_minutes') or 60)),
            preset_name=options.get('preset'),
        )
        if options.get('json'):
            self.stdout.write(json.dumps(payload, indent=2, sort_keys=True, default=str))
            return

        summary = payload.get('execution_exposure_release_audit_summary') or {}
        examples = payload.get('execution_exposure_release_audit_examples') or []
        self.stdout.write('Execution exposure release audit (diagnostic-only)')
        self.stdout.write('---------------------------------------------------')
        self.stdout.write(f"preset={payload.get('preset_name')} window_minutes={payload.get('window_minutes')}")
        self.stdout.write(
            f"suppressions_audited={summary.get('suppressions_audited', 0)} "
            f"keep_blocked={summary.get('keep_blocked_count', 0)} "
            f"release_eligible={summary.get('release_eligible_count', 0)} "
            f"pending_confirmation={summary.get('release_pending_confirmation_count', 0)} "
            f"manual_review={summary.get('manual_review_required_count', 0)}"
        )
        self.stdout.write(f"release_audit_summary={summary.get('release_audit_summary', '')}")
        self.stdout.write(f"examples={json.dumps(examples, default=str)}")
