import uuid

from django.db import models


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        "api.User",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="%(class)s_created_by",
    )
    updated_on = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        "api.User",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="%(class)s_updated_by",
    )
    is_deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True
