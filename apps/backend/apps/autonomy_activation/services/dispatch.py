from __future__ import annotations

from apps.autonomy_campaign.services import start_campaign


def dispatch_campaign_start(*, campaign, actor: str):
    return start_campaign(campaign=campaign, actor=actor)
