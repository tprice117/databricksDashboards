from django.db import models

from common.models import BaseModel


class OrderLineItemType(BaseModel):
    name = models.CharField(max_length=255)
    units = models.CharField(max_length=255)
    code = models.CharField(max_length=255)
    stripe_tax_code_id = models.CharField(max_length=255)

    def __str__(self):
        return self.name
