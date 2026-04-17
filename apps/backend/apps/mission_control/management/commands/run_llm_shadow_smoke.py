from __future__ import annotations

import json
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db.utils import OperationalError
from django.test.utils import override_settings

from apps.mission_control.services.llm_aux_signal import build_llm_aux_signal_summary
from apps.mission_control.services.llm_shadow import build_llm_shadow_summary


_DEFAULT_FOCUS_CASE = {
    'market_id': None,
    'handoff_id': 101,
    'prediction_candidate_id': 202,
    'risk_decision_id': 303,
    'shortlist_signal_id': 404,
    'headline': 'Synthetic focus: macro risk appetite cooling while event volatility remains elevated.',
    'risk_note': 'Potential sudden repricing around policy headlines.',
}


class Command(BaseCommand):
    help = 'Run a short local smoke test for the Mission Control LLM shadow + aux-signal chain.'

    def add_arguments(self, parser):
        parser.add_argument('--model', type=str, help='Override Ollama model just for this smoke run.')
        parser.add_argument('--timeout', type=int, help='Override Ollama timeout seconds just for this smoke run.')
        parser.add_argument(
            '--aux-signal',
            dest='aux_signal',
            action='store_true',
            default=None,
            help='Force-enable LLM auxiliary signal for this smoke run.',
        )
        parser.add_argument(
            '--no-aux-signal',
            dest='aux_signal',
            action='store_false',
            help='Force-disable LLM auxiliary signal for this smoke run.',
        )
        parser.add_argument(
            '--json',
            action='store_true',
            help='Emit compact JSON output instead of a text report.',
        )

    def handle(self, *args, **options):
        settings_overrides: dict[str, Any] = {}
        if options.get('model'):
            settings_overrides['OLLAMA_MODEL'] = str(options['model']).strip()
        if options.get('timeout') is not None:
            timeout = int(options['timeout'])
            if timeout <= 0:
                raise CommandError('--timeout must be greater than zero.')
            settings_overrides['OLLAMA_TIMEOUT_SECONDS'] = timeout
        if options.get('aux_signal') is not None:
            settings_overrides['OLLAMA_AUX_SIGNAL_ENABLED'] = bool(options['aux_signal'])

        payload = {
            'validation_status': 'OK',
            'trial_status': 'READY',
            'trend_status': 'STABLE',
            'readiness_status': 'PAPER_READY',
            'gate_status': 'SHADOW_ONLY',
            'reason_codes': ['SMOKE_LLM_MINIMAL_CASE'],
            'runtime_session_id': None,
            'test_run_reference': 'llm-shadow-smoke-local',
            'preset_name': 'llm-shadow-smoke',
            'paper_trade_final_summary': {
                'advisory_only': True,
                'affects_execution': False,
                'paper_only': True,
            },
        }
        funnel = {
            'funnel_status': 'ACTIVE',
            'top_stage': 'prediction_risk',
            'stalled_stage': 'none',
            'stalled_reason_code': None,
            'handoff_reason_codes': ['SMOKE_CASE'],
            'handoff_summary': 'Minimal realistic smoke case for local Ollama integration validation.',
            'prediction_intake_summary': {
                'status': 'ACTIVE',
                'candidate_count': 1,
            },
            'prediction_risk_summary': {
                'status': 'CAUTION',
                'risk_level': 'medium',
            },
            'prediction_risk_caution_summary': {
                'caution_level': 'medium',
                'reason_codes': ['VOLATILITY_EVENT_WINDOW'],
            },
            'prediction_status_summary': {
                'status': 'ACTIVE',
                'reason_codes': ['SMOKE_CHAIN_VALIDATION'],
            },
            'position_exposure_summary': {
                'open_positions_detected': 0,
                'position_exposure_reason_codes': ['POSITION_EXPOSURE_NONE'],
            },
            'cash_pressure_summary': {
                'cash_pressure_status': 'OK',
                'cash_pressure_reason_codes': ['CASH_PRESSURE_OK'],
            },
            'prediction_risk_examples': [_DEFAULT_FOCUS_CASE],
        }

        try:
            with override_settings(**settings_overrides):
                llm_shadow_summary = build_llm_shadow_summary(payload=payload, funnel=funnel)
                payload['llm_shadow_summary'] = llm_shadow_summary
                payload['latest_llm_shadow_summary'] = dict(llm_shadow_summary.get('latest_llm_shadow_summary') or llm_shadow_summary)
                payload['llm_aux_signal_summary'] = build_llm_aux_signal_summary(payload=payload)
        except OperationalError as exc:
            raise CommandError(
                'LLM smoke test could not access mission-control tables. Run migrations first (python manage.py migrate).'
            ) from exc

        result = {
            'ollama_responded': llm_shadow_summary.get('llm_shadow_reasoning_status') == 'OK',
            'provider': llm_shadow_summary.get('provider'),
            'model': llm_shadow_summary.get('model'),
            'llm_shadow_reasoning_status': llm_shadow_summary.get('llm_shadow_reasoning_status'),
            'summary': llm_shadow_summary.get('summary'),
            'key_risks': list(llm_shadow_summary.get('key_risks') or []),
            'key_supporting_points': list(llm_shadow_summary.get('key_supporting_points') or []),
            'artifact_persisted': llm_shadow_summary.get('artifact_id') is not None,
            'artifact_id': llm_shadow_summary.get('artifact_id'),
            'llm_aux_signal_summary': payload.get('llm_aux_signal_summary') or {},
            'boundaries': {
                'advisory_only': bool(llm_shadow_summary.get('advisory_only', True)),
                'affects_execution': bool((payload.get('llm_aux_signal_summary') or {}).get('affects_execution', False)),
                'paper_only': bool((payload.get('llm_aux_signal_summary') or {}).get('paper_only', True)),
            },
            'llm_error': None if llm_shadow_summary.get('llm_shadow_reasoning_status') == 'OK' else llm_shadow_summary.get('summary'),
        }

        if options.get('json'):
            self.stdout.write(json.dumps(result, indent=2, sort_keys=True, default=str))
            return

        self.stdout.write('Mission Control LLM shadow smoke test (short/local)')
        self.stdout.write('--------------------------------------------------')
        self.stdout.write(f"ollama_responded={result['ollama_responded']}")
        self.stdout.write(f"provider={result['provider']} model={result['model']}")
        self.stdout.write(f"llm_shadow_reasoning_status={result['llm_shadow_reasoning_status']}")
        self.stdout.write(f"summary={result['summary']}")
        self.stdout.write(f"key_risks={result['key_risks']}")
        self.stdout.write(f"key_supporting_points={result['key_supporting_points']}")
        self.stdout.write(f"artifact_persisted={result['artifact_persisted']} artifact_id={result['artifact_id']}")
        self.stdout.write(f"llm_aux_signal_summary={json.dumps(result['llm_aux_signal_summary'], sort_keys=True, default=str)}")
        self.stdout.write(
            'boundaries='
            + f"advisory_only={result['boundaries']['advisory_only']} "
            + f"affects_execution={result['boundaries']['affects_execution']} "
            + f"paper_only={result['boundaries']['paper_only']}"
        )

        if result['llm_error']:
            self.stdout.write(self.style.WARNING(f"llm_error={result['llm_error']}"))
        else:
            self.stdout.write(self.style.SUCCESS('llm_error=none'))
