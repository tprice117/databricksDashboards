from django.db import models

from api.models.main_product.add_on import AddOn
from api.models.main_product.main_product import MainProduct
from common.models import BaseModel


class MainProductAddOn(BaseModel):
    main_product = models.ForeignKey(MainProduct, models.CASCADE)
    add_on = models.ForeignKey(AddOn, models.CASCADE)

    def __str__(self):
        return f"{self.main_product.name} - {self.add_on.name}"
