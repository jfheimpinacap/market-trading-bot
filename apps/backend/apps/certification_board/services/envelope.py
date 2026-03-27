from decimal import Decimal

from apps.certification_board.models import CertificationEvidenceSnapshot, CertificationLevel, OperatingEnvelope


def build_operating_envelope(*, level: str, snapshot: CertificationEvidenceSnapshot) -> OperatingEnvelope:
    portfolio = snapshot.portfolio_governor_summary or {}
    runtime = snapshot.runtime_safety_summary or {}

    base_max_entries = int(portfolio.get('max_new_positions') or 1)
    base_size = Decimal(str(portfolio.get('max_size_multiplier') or 1))

    if level in {CertificationLevel.NOT_CERTIFIED, CertificationLevel.REMEDIATION_REQUIRED, CertificationLevel.RECERTIFICATION_REQUIRED}:
        return OperatingEnvelope.objects.create(
            max_autonomy_mode_allowed='PAPER_ASSIST',
            max_new_entries_per_cycle=max(1, min(base_max_entries, 1)),
            max_size_multiplier_allowed=min(base_size, Decimal('0.75')),
            auto_execution_allowed=False,
            canary_rollout_allowed=False,
            aggressive_profiles_disallowed=True,
            defensive_profiles_only=True,
            allowed_profiles=['conservative'],
            constrained_modules=['runtime', 'rollout', 'promotion'],
            notes='Certification not sufficient for broader paper autonomy.',
            constraints=['Manual approvals required for all entries.'],
        )

    if level == CertificationLevel.PAPER_CERTIFIED_DEFENSIVE:
        return OperatingEnvelope.objects.create(
            max_autonomy_mode_allowed='PAPER_SEMI_AUTO',
            max_new_entries_per_cycle=max(1, min(base_max_entries, 2)),
            max_size_multiplier_allowed=min(base_size, Decimal('1.00')),
            auto_execution_allowed=False,
            canary_rollout_allowed=False,
            aggressive_profiles_disallowed=True,
            defensive_profiles_only=True,
            allowed_profiles=['conservative', 'balanced'],
            constrained_modules=['rollout'],
            notes='Defensive paper envelope due to cautionary evidence.',
            constraints=['No aggressive profiles.', 'Manual review for non-defensive profile changes.'],
        )

    if level == CertificationLevel.PAPER_CERTIFIED_BALANCED:
        return OperatingEnvelope.objects.create(
            max_autonomy_mode_allowed='PAPER_SEMI_AUTO',
            max_new_entries_per_cycle=max(2, min(base_max_entries, 3)),
            max_size_multiplier_allowed=min(base_size, Decimal('1.25')),
            auto_execution_allowed=runtime.get('safety_status') == 'HEALTHY',
            canary_rollout_allowed=True,
            aggressive_profiles_disallowed=True,
            defensive_profiles_only=False,
            allowed_profiles=['conservative', 'balanced'],
            constrained_modules=[],
            notes='Balanced paper envelope with canary allowed.',
            constraints=['Aggressive profiles remain blocked pending high-autonomy certification.'],
        )

    return OperatingEnvelope.objects.create(
        max_autonomy_mode_allowed='PAPER_AUTO',
        max_new_entries_per_cycle=max(3, min(base_max_entries, 4)),
        max_size_multiplier_allowed=min(base_size, Decimal('1.50')),
        auto_execution_allowed=runtime.get('safety_status') == 'HEALTHY',
        canary_rollout_allowed=True,
        aggressive_profiles_disallowed=False,
        defensive_profiles_only=False,
        allowed_profiles=['conservative', 'balanced', 'aggressive_light'],
        constrained_modules=[],
        notes='Higher paper autonomy envelope, still paper/demo-only and manual-governed.',
        constraints=['Real-money execution remains disabled by design.'],
    )
