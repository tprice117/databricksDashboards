from django.db import models

from api.models.main_product.add_on import AddOn
from common.models import BaseModel


class AddOnChoice(BaseModel):
    name = models.CharField(max_length=80)
    add_on = models.ForeignKey(AddOn, models.CASCADE)

    def __str__(self):
        return f"{self.add_on.main_product.name} - {self.add_on.name} - {self.name}"
