from __future__ import annotations

from apps.champion_challenger.models import StackProfileBinding
from apps.experiment_lab.models import ExperimentCandidate


def map_baseline_and_challenger(*, candidate: ExperimentCandidate) -> dict:
    champion = StackProfileBinding.objects.filter(is_champion=True, is_active=True).order_by('-updated_at', '-id').first()
    baseline_label = champion.name if champion else candidate.baseline_reference
    return {
        'baseline_label': baseline_label,
        'challenger_label': candidate.challenger_label,
        'metadata': {
            'champion_binding_id': champion.id if champion else None,
            'target_component': candidate.metadata.get('target_component') if candidate.metadata else None,
        },
    }
