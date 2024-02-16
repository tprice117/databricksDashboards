from django.db import models

from api.models.main_product.product import Product
from api.models.seller.seller import Seller
from common.models import BaseModel


class SellerProduct(BaseModel):
    product = models.ForeignKey(
        Product,
        models.CASCADE,
        related_name="seller_products",
    )
    seller = models.ForeignKey(
        Seller,
        models.CASCADE,
        related_name="seller_products",
    )
    active = models.BooleanField(default=True)

    def __str__(self):
        return (
            self.product.main_product.name
            + " - "
            + (self.product.product_code or "")
            + " - "
            + self.seller.name
        )

    class Meta:
        unique_together = (
            "product",
            "seller",
        )
