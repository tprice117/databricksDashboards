from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver

from api.models.seller.delivery.seller_product_seller_location_delivery import (
    SellerProductSellerLocationDelivery,
)
from common.models import BaseModel


class SellerProductSellerLocationDeliveryPerMile(BaseModel):
    """
    NOT CURRENTLY IN USE. CONCEPT FOR FUTURE-USE ONLY.
    """

    seller_product_seller_location = models.OneToOneField(
        SellerProductSellerLocationDelivery,
        on_delete=models.CASCADE,
        related_name="per_mile",
    )
    price_per_mile = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    def get_price(
        self,
        miles: float,
    ) -> float:
        return self.price_per_mile * miles


@receiver(pre_save, sender=SellerProductSellerLocationDeliveryPerMile)
def pre_save_seller_product_seller_location_delivery_per_mile(
    sender,
    instance: SellerProductSellerLocationDeliveryPerMile,
    **kwargs,
):
    """
    Prevents creation of a SellerProductSellerLocationDeliveryPerMile if the
    SellerProductSellerLocationDelivery already has a flat rate delivery fee.
    """
    if instance._state.adding and hasattr(
        instance.seller_product_seller_location, "flat_rate"
    ):
        raise ValidationError(
            "A SellerProductSellerLocationDeliveryPerMile cannot be created if the "
            "SellerProductSellerLocationDelivery already has a flat rate delivery fee."
        )
