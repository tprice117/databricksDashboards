from django.db import models

from common.models import BaseModel


class OrderGroupRental(BaseModel):
    order_group = models.OneToOneField(
        "api.OrderGroup",
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

    def update_pricing(self):
        """
        Based on the OrderGroup.SellerProductSellerLocation's pricing, update the pricing.
        """
        self.included_days = (
            self.order_group.seller_product_seller_location.rental.included_days
        )
        self.price_per_day_included = (
            self.order_group.seller_product_seller_location.rental.price_per_day_included
        )
        self.price_per_day_additional = (
            self.order_group.seller_product_seller_location.rental.price_per_day_additional
        )
        self.save()
