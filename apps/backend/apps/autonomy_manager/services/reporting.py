from __future__ import annotations

from apps.autonomy_manager.models import AutonomyStage, AutonomyStageState, AutonomyStageTransition, AutonomyTransitionStatus


def build_autonomy_summary() -> dict:
    states = AutonomyStageState.objects.select_related('domain').all()
    transitions = AutonomyStageTransition.objects.all()
    return {
        'total_domains': states.count(),
        'manual_domains': states.filter(current_stage=AutonomyStage.MANUAL).count(),
        'assisted_domains': states.filter(current_stage=AutonomyStage.ASSISTED).count(),
        'supervised_autopilot_domains': states.filter(current_stage=AutonomyStage.SUPERVISED_AUTOPILOT).count(),
        'frozen_domains': states.filter(current_stage=AutonomyStage.FROZEN).count(),
        'degraded_domains': states.filter(status='DEGRADED').count(),
        'blocked_domains': states.filter(status='BLOCKED').count(),
        'pending_stage_changes': transitions.filter(status__in=[AutonomyTransitionStatus.PENDING_APPROVAL, AutonomyTransitionStatus.READY_TO_APPLY]).count(),
        'applied_transitions': transitions.filter(status=AutonomyTransitionStatus.APPLIED).count(),
        'rolled_back_transitions': transitions.filter(status=AutonomyTransitionStatus.ROLLED_BACK).count(),
    }
