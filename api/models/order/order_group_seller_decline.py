from django.db import models

from api.models.seller.seller_product_seller_location import SellerProductSellerLocation
from common.models import BaseModel


class OrderGroupSellerDecline(BaseModel):
    order_group = models.ForeignKey(
        "api.OrderGroup",
        models.CASCADE,
    )
    seller_product_seller_location = models.ForeignKey(
        SellerProductSellerLocation,
        models.CASCADE,
        related_name="order_group_seller_declines",
    )

    class Meta:
        verbose_name = "Booking Seller Decline"
        verbose_name_plural = "Booking Seller Declines"
