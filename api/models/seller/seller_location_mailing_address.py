from django.db import models
from django.db.models.signals import pre_save

from api.models.seller.seller_location import SellerLocation
from api.utils.google_maps import geocode_address
from common.models import BaseModel


class SellerLocationMailingAddress(BaseModel):
    seller_location = models.OneToOneField(
        SellerLocation, models.CASCADE, related_name="mailing_address"
    )
    street = models.TextField()
    city = models.CharField(max_length=40)
    state = models.CharField(max_length=80)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=80)
    latitude = models.DecimalField(max_digits=18, decimal_places=15, blank=True)
    longitude = models.DecimalField(max_digits=18, decimal_places=15, blank=True)

    def pre_save(sender, instance, *args, **kwargs):
        latitude, longitude = geocode_address(
            f"{instance.street} {instance.city} {instance.state} {instance.postal_code}"
        )
        instance.latitude = latitude or 0
        instance.longitude = longitude or 0


pre_save.connect(
    SellerLocationMailingAddress.pre_save, sender=SellerLocationMailingAddress
)
