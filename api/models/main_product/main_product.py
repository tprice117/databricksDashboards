from django.db import models

from api.models.main_product.main_product_category import MainProductCategory
from common.models import BaseModel


class MainProduct(BaseModel):
    name = models.CharField(max_length=80)
    cubic_yards = models.IntegerField(blank=True, null=True)
    ar_url = models.URLField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    image_del = models.TextField(blank=True, null=True)
    main_product_category = models.ForeignKey(MainProductCategory, models.CASCADE)
    sort = models.IntegerField()
    included_tonnage_quantity = models.DecimalField(
        max_digits=18, decimal_places=0, blank=True, null=True
    )
    price_per_additional_ton = models.DecimalField(
        max_digits=18, decimal_places=2, blank=True, null=True
    )
    max_tonnage_quantity = models.DecimalField(
        max_digits=18, decimal_places=0, blank=True, null=True
    )
    max_rate = models.DecimalField(
        max_digits=18, decimal_places=0, blank=True, null=True
    )
    included_rate_quantity = models.DecimalField(
        max_digits=18, decimal_places=0, blank=True, null=True
    )
    main_product_code = models.CharField(max_length=255, blank=True, null=True)
    has_service = models.BooleanField(default=False)
    has_rental = models.BooleanField(default=False)
    has_material = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.main_product_category.name} - {self.name}"
