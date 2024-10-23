from django.db import models

from api.models.main_product.main_product import MainProduct
from common.models import BaseModel


class MainProductInfo(BaseModel):
    name = models.CharField(max_length=80)
    description = models.CharField(max_length=255)
    main_product = models.ForeignKey(MainProduct, models.CASCADE)
    sort = models.IntegerField()

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Product Info"
        verbose_name_plural = "Product Infos"
