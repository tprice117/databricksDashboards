from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver

from api.models import MainProduct, SellerLocation
from api.models.track_data import track_data
from asset_management.models.asset_model import AssetModel
from common.models import BaseModel


@track_data("seller_location")
class Asset(BaseModel):
    seller_location = models.ForeignKey(
        SellerLocation,
        on_delete=models.PROTECT,
    )
    main_product = models.ForeignKey(
        MainProduct,
        on_delete=models.PROTECT,
    )
    model = models.ForeignKey(
        AssetModel,
        on_delete=models.PROTECT,
    )
    year = models.IntegerField(
        validators=[MinValueValidator(1950), MaxValueValidator(2100)]
    )
    serial_number = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.year} {self.model} - {self.serial_number}"


@receiver(pre_save, sender=Asset)
def asset_pre_save(sender, instance: Asset, **kwargs):
    # If the asset is being updated and the seller location has changed, ensure both
    # SellerLocation instances are associated with the same seller.
    if not instance._state.adding and instance.has_changed("seller_location"):
        old_seller_location = instance.old_value("seller_location")
        new_seller_location = instance.seller_location.seller
        if old_seller_location != new_seller_location:
            raise ValidationError(
                "The new SellerLocation must be associated with the same Seller."
            )
