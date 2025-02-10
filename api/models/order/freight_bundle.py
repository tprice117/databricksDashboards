from django.db import models
from common.models import BaseModel


class FreightBundle(BaseModel):
    # user_address = models.ForeignKey(
    #     UserAddress,
    #     models.PROTECT,
    #     related_name="bundles",
    # )
    name = models.CharField(max_length=255, blank=True, null=True)
    delivery_fee = models.DecimalField(
        max_digits=18, decimal_places=2, default=0, blank=True, null=True
    )
    removal_fee = models.DecimalField(
        max_digits=18, decimal_places=2, default=0, blank=True, null=True
    )

    # class Meta:
    #     verbose_name = "Bundle"
    #     verbose_name_plural = "Bundles"

    def __str__(self):
        return f"{self.name or 'Freight Bundle'}"

    def delete(self):
        # recalculate all the order line items
        for order_group in self.order_groups.all():
            for order in order_group.orders.all():
                order.order_line_items.all().delete()
                order.add_line_items(True)
                order.order_group.delivery_fee = (
                    order.order_group.seller_product_seller_location.delivery_fee
                )
                order.order_group.removal_fee = (
                    order.order_group.seller_product_seller_location.removal_fee
                )
                order.order_group.save()
        super().delete()
