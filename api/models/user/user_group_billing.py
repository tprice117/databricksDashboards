from django.db import models
from django.db.models.signals import pre_save, post_save
import threading

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

    def update_stripe(self):
        addresses = self.user_group.user_addresses.all()
        for address in addresses:
            address.update_stripe(save_on_update=True)

    def pre_save(sender, instance, *args, **kwargs):
        latitude, longitude = geocode_address(
            f"{instance.street} {instance.city} {instance.state} {instance.postal_code}"
        )
        instance.latitude = latitude or 0
        instance.longitude = longitude or 0

    def post_save(sender, instance, *args, **kwargs):
        # Note: This is done asynchronously because it is not critical and shouldn't cause page to hang.
        p = threading.Thread(target=instance.update_stripe)
        p.start()


pre_save.connect(UserGroupBilling.pre_save, sender=UserGroupBilling)
post_save.connect(UserGroupBilling.post_save, sender=UserGroupBilling)
