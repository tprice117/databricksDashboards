from django.db import models

from api.models.main_product.main_product_category import MainProductCategory
from common.models import BaseModel


class MainProductCategoryInfo(BaseModel):
    name = models.CharField(max_length=80)
    main_product_category = models.ForeignKey(MainProductCategory, models.CASCADE)
    sort = models.IntegerField()

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Product Category Info"
        verbose_name_plural = "Product Category Infos"
