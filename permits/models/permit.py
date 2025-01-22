from django.db import models

from common.models import BaseModel


class Permit(BaseModel):
    """
    A Permit is a license or other form of permission to do something,
    typically granted by a city or other government organization.
    """

    name = models.CharField(max_length=255)
    description = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    def __str__(self):
        return self.name
