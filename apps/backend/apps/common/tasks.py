from celery import shared_task


@shared_task
def ping() -> str:
    """Simple placeholder task for Celery wiring verification."""

    return 'pong'
