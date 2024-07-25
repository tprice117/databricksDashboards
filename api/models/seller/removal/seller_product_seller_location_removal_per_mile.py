from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver

from api.models.seller.removal.seller_product_seller_location_removal import (
    SellerProductSellerLocationRemoval,
)
from common.models import BaseModel


class SellerProductSellerLocationRemovalPerMile(BaseModel):
    """
    NOT CURRENTLY IN USE. CONCEPT FOR FUTURE-USE ONLY.
    """

    seller_product_seller_location = models.OneToOneField(
        SellerProductSellerLocationRemoval,
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


@receiver(pre_save, sender=SellerProductSellerLocationRemovalPerMile)
def pre_save_seller_product_seller_location_delivery_per_mile(
    sender,
    instance: SellerProductSellerLocationRemovalPerMile,
    **kwargs,
):
    """
    Prevents creation of a SellerProductSellerLocationRemovalPerMile if the
    SellerProductSellerLocationRemoval already has a flat rate delivery fee.
    """
    if instance._state.adding and hasattr(
        instance.seller_product_seller_location, "flat_rate"
    ):
        raise ValidationError(
            "A SellerProductSellerLocationRemovalPerMile cannot be created if the "
            "SellerProductSellerLocationRemoval already has a flat rate delivery fee."
        )
