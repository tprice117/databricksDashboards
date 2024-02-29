from django.db import models
from django.db.models.signals import pre_save

from api.models.user.user import User
from api.models.user.user_address_type import UserAddressType
from api.models.user.user_group import UserGroup
from api.utils.google_maps import geocode_address
from common.models import BaseModel
from common.utils.stripe.stripe_utils import StripeUtils


class UserAddress(BaseModel):
    user_group = models.ForeignKey(
        UserGroup,
        models.CASCADE,
        related_name="user_addresses",
        blank=True,
        null=True,
    )
    user = models.ForeignKey(
        User,
        models.CASCADE,
        blank=True,
        null=True,
    )
    user_address_type = models.ForeignKey(
        UserAddressType,
        models.CASCADE,
        blank=True,
        null=True,
    )
    stripe_customer_id = models.CharField(
        max_length=255,
        blank=True,
        unique=True,
    )
    name = models.CharField(max_length=255, blank=True, null=True)
    project_id = models.CharField(max_length=50, blank=True, null=True)
    street = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=40)
    state = models.CharField(max_length=80)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=80)
    latitude = models.DecimalField(max_digits=18, decimal_places=15, blank=True)
    longitude = models.DecimalField(max_digits=18, decimal_places=15, blank=True)
    access_details = models.TextField(blank=True, null=True)
    autopay = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    child_account_id = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.name or "[No name]"

    def formatted_address(self):
        return f"{self.street} {self.city}, {self.state} {self.postal_code}"

    def pre_save(sender, instance, *args, **kwargs):
        # Populate latitude and longitude.
        latitude, longitude = geocode_address(
            f"{instance.street} {instance.city} {instance.state} {instance.postal_code}"
        )
        instance.latitude = latitude or 0
        instance.longitude = longitude or 0

        # Populate Stripe Customer ID, if not already populated.
        if not instance.stripe_customer_id:
            print("TEST")
            customer = StripeUtils.Customer.create()
            instance.stripe_customer_id = customer.id
        else:
            print("TEST2")
            customer = StripeUtils.Customer.get(instance.stripe_customer_id)

        # Get "name" for UserGroup/B2C user.
        user_group_name = instance.user_group.name if instance.user_group else "[B2C]"

        customer = StripeUtils.Customer.update(
            customer.id,
            name=user_group_name + " | " + instance.formatted_address(),
            email=(
                instance.user_group.billing.email
                if hasattr(instance.user_group, "billing")
                else (instance.user.email if instance.user else None)
            ),
            # phone = instance.user_group.billing.phone if hasattr(instance.user_group, 'billing') else instance.user.phone,
            shipping={
                "name": instance.name or instance.formatted_address(),
                "address": {
                    "line1": instance.street,
                    "city": instance.city,
                    "state": instance.state,
                    "postal_code": instance.postal_code,
                    "country": "US",
                },
            },
            address={
                "line1": (
                    instance.user_group.billing.street
                    if hasattr(instance.user_group, "billing")
                    else instance.street
                ),
                "city": (
                    instance.user_group.billing.city
                    if hasattr(instance.user_group, "billing")
                    else instance.city
                ),
                "state": (
                    instance.user_group.billing.state
                    if hasattr(instance.user_group, "billing")
                    else instance.state
                ),
                "postal_code": (
                    instance.user_group.billing.postal_code
                    if hasattr(instance.user_group, "billing")
                    else instance.postal_code
                ),
                "country": "US",
                # "country": instance.user_group.billing.country
                # if hasattr(instance.user_group, "billing")
                # else instance.country,
            },
            metadata={
                "user_group_id": (
                    str(instance.user_group.id) if instance.user_group else None
                ),
                "user_address_id": str(instance.id),
                "user_id": str(instance.user.id) if instance.user else None,
            },
            tax_exempt=(
                instance.user_group.tax_exempt_status
                if hasattr(instance.user_group, "billing")
                else UserGroup.TaxExemptStatus.NONE
            ),
        )


pre_save.connect(UserAddress.pre_save, sender=UserAddress)
