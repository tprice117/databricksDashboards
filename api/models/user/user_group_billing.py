from django.db import models
from django.db.models.signals import pre_save, post_save

from api.models.user.user_group import UserGroup
from api.utils.google_maps import geocode_address
from common.models import BaseModel


class UserGroupBilling(BaseModel):
    user_group = models.OneToOneField(UserGroup, models.CASCADE, related_name="billing")
    email = models.EmailField()
    # phone = models.CharField(max_length=40, blank=True, null=True)
    tax_id = models.CharField(max_length=255, blank=True, null=True)
    street = models.TextField()
    city = models.CharField(max_length=40)
    state = models.CharField(max_length=80)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=80)
    latitude = models.DecimalField(max_digits=18, decimal_places=15, blank=True)
    longitude = models.DecimalField(max_digits=18, decimal_places=15, blank=True)

    @property
    def formatted_address(self):
        return f"{self.street} {self.city}, {self.state} {self.postal_code}"

    def pre_save(sender, instance, *args, **kwargs):
        latitude, longitude = geocode_address(
            f"{instance.street} {instance.city} {instance.state} {instance.postal_code}"
        )
        instance.latitude = latitude or 0
        instance.longitude = longitude or 0

    def post_save(sender, instance, *args, **kwargs):
        # Get first address from user_group
        user_group = instance.user_group
        addresses = user_group.user_addresses.all()
        for address in addresses:
            address.update_stripe(save_on_update=True)


pre_save.connect(UserGroupBilling.pre_save, sender=UserGroupBilling)
post_save.connect(UserGroupBilling.post_save, sender=UserGroupBilling)
