from django.db import models

from common.models import BaseModel


class OrderGroupService(BaseModel):
    order_group = models.OneToOneField(
        "api.OrderGroup",
        on_delete=models.CASCADE,
        related_name="service",
    )
    rate = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    miles = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)

    def update_pricing(self):
        """
        Based on the OrderGroup.SellerProductSellerLocation's pricing, update the pricing.
        """
        self.rate = self.order_group.seller_product_seller_location.service.rate
        self.miles = self.order_group.seller_product_seller_location.service.miles
        self.save()
