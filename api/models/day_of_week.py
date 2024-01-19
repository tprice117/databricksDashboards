from django.db import models

from common.models import BaseModel


class DayOfWeek(BaseModel):
    name = models.CharField(max_length=80)
    number = models.IntegerField()

    def __str__(self):
        return self.name
