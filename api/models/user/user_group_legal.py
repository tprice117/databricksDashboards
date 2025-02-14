from django.db import models
from django.db.models.signals import pre_save

from api.models.user.user_group import UserGroup
from api.utils.google_maps import geocode_address
from common.models import BaseModel


class UserGroupLegal(BaseModel):
    class BusinessStructure(models.TextChoices):
        SOLE_PROPRIETORSHIP = "sole_proprietorship"
        LLC = "llc"
        S_CORP = "s_corp"
        C_CORP = "c_corp"
        OTHER = "other"

    class Industry(models.TextChoices):
        PROPERTY_MANAGEMENT = "property_management"
        CONSTRUCTION = "construction"
        MANUFACTURING = "manufacturing"
        WASTE_COLLECTION = "waste_collection"
        OTHER = "other"

    user_group = models.OneToOneField(UserGroup, models.CASCADE, related_name="legal")
    name = models.CharField(max_length=255)
    tax_id = models.CharField(
        max_length=20, blank=True, null=True, help_text="EIN/TIN or SSN"
    )
    accepted_net_terms = models.BooleanField(default=False)
    years_in_business = models.PositiveIntegerField(blank=True, null=True)
    doing_business_as = models.CharField(max_length=255, blank=True, null=True)
    structure = models.CharField(max_length=20, choices=BusinessStructure.choices)
    industry = models.CharField(max_length=20, choices=Industry.choices)
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


pre_save.connect(UserGroupLegal.pre_save, sender=UserGroupLegal)
