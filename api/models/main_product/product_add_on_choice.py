from django.db import models

from api.models.main_product.add_on_choice import AddOnChoice
from common.models import BaseModel


class ProductAddOnChoice(BaseModel):
    name = models.CharField(max_length=80)
    product = models.ForeignKey(
        "api.Product",
        models.CASCADE,
        related_name="product_add_on_choices",
    )
    add_on_choice = models.ForeignKey(AddOnChoice, models.CASCADE)

    def __str__(self):
        return f"{self.product.main_product.name} - {self.add_on_choice.add_on.name} - {self.add_on_choice.name}"

    class Meta:
        verbose_name = "Product Variant Choice"
        verbose_name_plural = "Product Variants Choices"
        unique_together = (
            "product",
            "add_on_choice",
        )
