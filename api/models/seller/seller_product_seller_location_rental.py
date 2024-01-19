from django.db import models

from common.models import BaseModel


class SellerProductSellerLocationRental(BaseModel):
    seller_product_seller_location = models.OneToOneField(
        "api.SellerProductSellerLocation",
        on_delete=models.CASCADE,
        related_name="rental",
    )
    included_days = models.IntegerField(default=0)
    price_per_day_included = models.DecimalField(
        max_digits=18, decimal_places=2, default=0
    )
    price_per_day_additional = models.DecimalField(
        max_digits=18, decimal_places=2, default=0
    )

    def __str__(self):
        return self.seller_product_seller_location.seller_location.name
