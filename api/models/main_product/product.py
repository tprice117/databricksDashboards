from django.db import models

from api.models.main_product.main_product import MainProduct
from api.models.main_product.product_add_on_choice import ProductAddOnChoice
from common.models import BaseModel


class Product(BaseModel):
    product_code = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    main_product = models.ForeignKey(
        MainProduct,
        models.CASCADE,
        related_name="products",
    )
    removal_price = models.DecimalField(
        max_digits=18, decimal_places=2, blank=True, null=True
    )

    def __str__(self):
        add_on_choices = ProductAddOnChoice.objects.filter(product=self)
        return f'{self.main_product.name} {"-" if add_on_choices.count() > 0 else ""} {",".join(str(add_on_choice.name) for add_on_choice in add_on_choices)}'
