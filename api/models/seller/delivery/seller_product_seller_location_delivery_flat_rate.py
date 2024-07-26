from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver

from api.models.seller.delivery.seller_product_seller_location_delivery import (
    SellerProductSellerLocationDelivery,
)
from common.models import BaseModel


class SellerProductSellerLocationDeliveryFlatRate(BaseModel):
    """
    NOT CURRENTLY IN USE. CONCEPT FOR FUTURE-USE ONLY.
    """

    seller_product_seller_location = models.OneToOneField(
        SellerProductSellerLocationDelivery,
        on_delete=models.CASCADE,
        related_name="flat_rate",
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    def get_price(
        self,
    ) -> float:
        return self.price


@receiver(pre_save, sender=SellerProductSellerLocationDeliveryFlatRate)
def pre_save_seller_product_seller_location_delivery_flat_rate(
    sender,
    instance: SellerProductSellerLocationDeliveryFlatRate,
    **kwargs,
):
    """
    Prevents creation of a SellerProductSellerLocationDeliveryFlatRate if the
    SellerProductSellerLocationDelivery already has a per mile delivery fee.
    """
    if instance._state.adding and hasattr(
        instance.seller_product_seller_location, "per_mile"
    ):
        raise ValidationError(
            "A SellerProductSellerLocationDeliveryFlatRate cannot be created if the "
            "SellerProductSellerLocationDelivery already has a per mile delivery fee."
        )
