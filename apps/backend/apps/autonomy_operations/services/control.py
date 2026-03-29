from django.utils import timezone

from apps.autonomy_operations.models import CampaignAttentionSignal, CampaignAttentionSignalStatus


def acknowledge_signal(*, signal: CampaignAttentionSignal, actor: str = 'operator-ui') -> CampaignAttentionSignal:
    signal.status = CampaignAttentionSignalStatus.ACKNOWLEDGED
    signal.metadata = {
        **(signal.metadata or {}),
        'acknowledged_by': actor,
        'acknowledged_at': timezone.now().isoformat(),
    }
    signal.save(update_fields=['status', 'metadata', 'updated_at'])
    return signal
