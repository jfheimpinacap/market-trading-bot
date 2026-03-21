from django.db import models


class BaseModel(models.Model):
    """Base abstract model for shared ORM behavior."""

    class Meta:
        abstract = True


class TimeStampedModel(BaseModel):
    """Adds creation and update timestamps to inheriting models."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
