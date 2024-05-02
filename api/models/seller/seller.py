from django.db import models
from django.conf import settings
from multiselectfield import MultiSelectField

from common.models import BaseModel
from api.utils.utils import encrypt_string


class Seller(BaseModel):
    open_day_choices = (
        ("MONDAY", "MONDAY"),
        ("TUESDAY", "TUESDAY"),
        ("WEDNESDAY", "WEDNESDAY"),
        ("THURSDAY", "THURSDAY"),
        ("FRIDAY", "FRIDAY"),
        ("SATURDAY", "SATURDAY"),
        ("SUNDAY", "SUNDAY"),
    )

    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=40)
    website = models.URLField(blank=True, null=True)
    # START: Communicaton fields.
    order_email = models.CharField(max_length=255, blank=True, null=True)
    order_phone = models.CharField(max_length=10, blank=True, null=True)
    # END: Communicaton fields.
    type = models.CharField(
        max_length=255,
        choices=[
            ("Broker", "Broker"),
            ("Compost facility", "Compost facility"),
            ("Delivery", "Delivery"),
            ("Equipment", "Equipment"),
            ("Fencing", "Fencing"),
            ("Industrial", "Industrial"),
            ("Junk", "Junk"),
            ("Landfill", "Landfill"),
            ("Mover", "Mover"),
            ("MRF", "MRF"),
            ("Other recycler", "Other recycler"),
            ("Paint recycler", "Paint recycler"),
            ("Portable Storage", "Portable Storage"),
            ("Portable Toilet", "Portable Toilet"),
            ("Processor", "Processor"),
            ("Roll-off", "Roll-off"),
            ("Scrap yard", "Scrap yard"),
            ("Tires", "Tires"),
        ],
        blank=True,
        null=True,
    )
    location_type = models.CharField(
        max_length=255,
        choices=[("Services", "Services"), ("Disposal site", "Disposal site")],
        blank=True,
        null=True,
    )
    status = models.CharField(
        max_length=255,
        choices=[
            ("Inactive", "Inactive"),
            ("Inactive - Onboarding", "Inactive - Onboarding"),
            ("Inactive - Pending approval", "Inactive - Pending approval"),
            ("Active - under review", "Active - under review"),
            ("Active", "Active"),
        ],
        blank=True,
        null=True,
    )
    lead_time = models.CharField(max_length=255, blank=True, null=True)
    type_display = models.CharField(
        max_length=255,
        choices=[
            ("Landfill", "Landfill"),
            ("MRF", "MRF"),
            ("Industrial", "Industrial"),
            ("Scrap yard", "Scrap yard"),
            ("Compost facility", "Compost facility"),
            ("Processor", "Processor"),
            ("Paint recycler", "Paint recycler"),
            ("Tires", "Tires"),
            ("Other recycler", "Other recycler"),
            ("Roll-off", "Roll-off"),
            ("Mover", "Mover"),
            ("Junk", "Junk"),
            ("Delivery", "Delivery"),
            ("Broker", "Broker"),
            ("Equipment", "Equipment"),
        ],
        blank=True,
        null=True,
    )
    stripe_connect_id = models.CharField(max_length=255, blank=True, null=True)
    marketplace_display_name = models.CharField(max_length=255, blank=True, null=True)
    open_days = MultiSelectField(
        max_length=255, choices=open_day_choices, max_choices=7, blank=True, null=True
    )
    open_time = models.TimeField(blank=True, null=True)
    close_time = models.TimeField(blank=True, null=True)
    lead_time_hrs = models.DecimalField(
        max_digits=18, decimal_places=0, blank=True, null=True
    )
    announcement = models.TextField(blank=True, null=True)
    live_menu_is_active = models.BooleanField(default=False)
    location_logo_url = models.URLField(blank=True, null=True)
    downstream_insurance_requirements_met = models.BooleanField(default=False)
    badge = models.CharField(
        max_length=255,
        choices=[("New", "New"), ("Pro", "Pro"), ("Platinum", "Platinum")],
        blank=True,
        null=True,
    )
    salesforce_seller_id = models.CharField(max_length=255, blank=True, null=True)
    about_us = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

    @property
    def dashboard_url(self):
        """Returns the URL for the seller dashboard."""
        return f"{settings.API_URL}/supplier/{self.id}/dashboard/?key={encrypt_string(str(self.id))}"

    def get_dashboard_status_url(
        self, status: str, snippet_name="accordian_status_orders"
    ):
        """Returns the URL for the seller dashboard items with the specified status.
        This works in conjunction with the supplier dashboard view since it returns a subset of the orders based on the status.
        """
        return f"{settings.API_URL}/supplier/{self.id}/status/{status.lower()}/?key={encrypt_string(str(self.id))}&snippet_name={snippet_name}"
