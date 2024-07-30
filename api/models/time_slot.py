from django.db import models

from common.models import BaseModel


class TimeSlot(BaseModel):
    name = models.CharField(max_length=80)
    start = models.TimeField()
    end = models.TimeField()

    def __str__(self):
        return self.name
