from django.db import models

from common.models import BaseModel


class TimeSlot(BaseModel):
    name = models.CharField(max_length=80)
    start = models.TimeField()
    end = models.TimeField()

    def __str__(self):
        return self.name

    @staticmethod
    def get_all_time_slots():
        # Only return Anytime, Morning, Afternoon
        return TimeSlot.objects.filter(name__in=["Anytime", "Morning", "Afternoon"])
