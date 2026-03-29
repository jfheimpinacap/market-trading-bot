from __future__ import annotations

from apps.autonomy_closeout.models import CloseoutFindingType
from apps.autonomy_closeout.services.candidates import CloseoutCandidate


def derive_closeout_findings(candidate: CloseoutCandidate, summary: dict) -> list[dict]:
    findings: list[dict] = []

    if candidate.ready_for_closeout:
        findings.append(
            {
                'finding_type': CloseoutFindingType.SUCCESS_FACTOR,
                'severity_or_weight': 'LOW',
                'summary': 'Disposition applied cleanly with no unresolved blockers.',
                'reason_codes': ['clean_disposition_apply'],
                'recommended_followup': 'Complete closeout and archive dossier.',
                'metadata': {},
            }
        )

    if candidate.unresolved_blockers:
        findings.append(
            {
                'finding_type': CloseoutFindingType.BLOCKER_PATTERN,
                'severity_or_weight': 'HIGH',
                'summary': f"Unresolved blockers remain: {', '.join(candidate.unresolved_blockers)}.",
                'reason_codes': ['unresolved_blockers'],
                'recommended_followup': 'Require manual closeout review before completion.',
                'metadata': {},
            }
        )

    if candidate.unresolved_approvals_count > 0:
        findings.append(
            {
                'finding_type': CloseoutFindingType.APPROVAL_FRICTION,
                'severity_or_weight': 'MEDIUM',
                'summary': f"{candidate.unresolved_approvals_count} pending approvals are blocking final closeout.",
                'reason_codes': ['pending_approvals'],
                'recommended_followup': 'Resolve approval center queue first.',
                'metadata': {},
            }
        )

    if candidate.incident_history_level in {'MEDIUM', 'HIGH'}:
        findings.append(
            {
                'finding_type': CloseoutFindingType.INCIDENT_LESSON,
                'severity_or_weight': candidate.incident_history_level,
                'summary': 'Incident pressure materially affected campaign closure confidence.',
                'reason_codes': ['incident_pressure'],
                'recommended_followup': 'Prepare postmortem and incident commander follow-up artifacts.',
                'metadata': {'incident_summary': summary['incident_summary']},
            }
        )

    if summary['recovery_summary']['status']:
        findings.append(
            {
                'finding_type': CloseoutFindingType.RECOVERY_LESSON,
                'severity_or_weight': 'MEDIUM',
                'summary': f"Recovery status at disposition time: {summary['recovery_summary']['status']}.",
                'reason_codes': ['recovery_evidence_captured'],
                'recommended_followup': 'Attach recovery rationale to final dossier.',
                'metadata': {},
            }
        )

    findings.append(
        {
            'finding_type': CloseoutFindingType.DISPOSITION_LESSON,
            'severity_or_weight': 'MEDIUM',
            'summary': f"Disposition outcome was {candidate.disposition.disposition_type}.",
            'reason_codes': ['disposition_recorded'],
            'recommended_followup': 'Use disposition outcome in roadmap/scenario feedback where relevant.',
            'metadata': {'disposition_status': candidate.disposition.disposition_status},
        }
    )

    return findings
