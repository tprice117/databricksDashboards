from django.db import models

from api.models.main_product.main_product import MainProduct
from api.models.service_recurring_freqency import ServiceRecurringFrequency
from common.models import BaseModel


class MainProductServiceRecurringFrequency(BaseModel):
    main_product = models.ForeignKey(MainProduct, models.PROTECT)
    service_recurring_frequency = models.ForeignKey(
        ServiceRecurringFrequency, models.PROTECT
    )

    def __str__(self):
        return f"{self.main_product.name} - {self.service_recurring_frequency.name}"
