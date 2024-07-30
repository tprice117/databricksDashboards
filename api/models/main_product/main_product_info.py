from django.db import models

from api.models.main_product.main_product import MainProduct
from common.models import BaseModel


class MainProductInfo(BaseModel):
    name = models.CharField(max_length=80)
    main_product = models.ForeignKey(MainProduct, models.CASCADE)
    sort = models.IntegerField()

    def __str__(self):
        return self.name
