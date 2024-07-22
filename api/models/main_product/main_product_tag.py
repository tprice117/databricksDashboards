from django.db import models

from common.models import BaseModel


class MainProductTag(BaseModel):
    name = models.CharField(max_length=80)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
