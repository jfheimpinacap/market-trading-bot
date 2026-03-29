from django.utils import timezone

from apps.autonomy_scheduler.models import ChangeWindow, ChangeWindowStatus


def resolve_window_status(window: ChangeWindow) -> str:
    now = timezone.now()
    if window.status == ChangeWindowStatus.FROZEN:
        return ChangeWindowStatus.FROZEN
    if window.starts_at and window.starts_at > now:
        return ChangeWindowStatus.UPCOMING
    if window.ends_at and window.ends_at < now:
        return ChangeWindowStatus.CLOSED
    return ChangeWindowStatus.OPEN


def get_active_window() -> ChangeWindow | None:
    windows = ChangeWindow.objects.order_by('-created_at', '-id')
    for window in windows:
        status = resolve_window_status(window)
        if window.status != status:
            window.status = status
            window.save(update_fields=['status', 'updated_at'])
        if status in [ChangeWindowStatus.OPEN, ChangeWindowStatus.FROZEN]:
            return window
    return None
