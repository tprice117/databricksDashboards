import uuid
import datetime

from django.db import models
from django.db.models.signals import pre_save

from api.utils.google_maps import geocode_address
from common.models import BaseModel


class SellerLocation(BaseModel):
    def get_file_path(instance, filename):
        ext = filename.split(".")[-1]
        filename = "%s.%s" % (uuid.uuid4(), ext)
        return filename

    seller = models.ForeignKey(
        "api.Seller",
        models.CASCADE,
        related_name="seller_locations",
    )
    name = models.CharField(max_length=255)
    street = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=40)
    state = models.CharField(max_length=80)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=80)
    latitude = models.DecimalField(max_digits=18, decimal_places=15, blank=True)
    longitude = models.DecimalField(max_digits=18, decimal_places=15, blank=True)
    stripe_connect_account_id = models.CharField(max_length=255, blank=True, null=True)
    sends_invoices = models.BooleanField(default=False)
    # START: Pay-by-check fields.
    payee_name = models.CharField(max_length=255, blank=True, null=True)
    # END: Pay-by-check fields.
    # START: Communicaton fields.
    order_email = models.CharField(max_length=255, blank=True, null=True)
    order_phone = models.CharField(max_length=10, blank=True, null=True)
    # END: Communicaton fields.
    # START: Insurance and tax fields.
    gl_coi = models.FileField(upload_to=get_file_path, blank=True, null=True)
    gl_coi_expiration_date = models.DateField(blank=True, null=True)
    gl_limit = models.DecimalField(
        max_digits=18, decimal_places=2, blank=True, null=True
    )
    auto_coi = models.FileField(upload_to=get_file_path, blank=True, null=True)
    auto_coi_expiration_date = models.DateField(blank=True, null=True)
    auto_limit = models.DecimalField(
        max_digits=18, decimal_places=2, blank=True, null=True
    )
    workers_comp_coi = models.FileField(upload_to=get_file_path, blank=True, null=True)
    workers_comp_coi_expiration_date = models.DateField(blank=True, null=True)
    workers_comp_limit = models.DecimalField(
        max_digits=18, decimal_places=2, blank=True, null=True
    )
    w9 = models.FileField(upload_to=get_file_path, blank=True, null=True)
    # END: Insurance and tax fields.

    def __str__(self):
        return self.name

    @property
    def formatted_address(self):
        return f"{self.street} {self.city}, {self.state} {self.postal_code}"

    @property
    def is_insurance_expiring_soon(self):
        """Returns true if any of the insurance policies are expiring within 60 days.
        NOTE: Null expiration dates will not trigger this, that case is considered non compliant.
        """
        today = datetime.date.today()
        grace_date = today - datetime.timedelta(days=60)
        if (
            self.gl_coi_expiration_date
            and self.auto_coi_expiration_date
            and self.workers_comp_coi_expiration_date
        ):
            return (
                (
                    self.gl_coi_expiration_date >= grace_date
                    and today <= self.gl_coi_expiration_date
                )
                or (
                    self.auto_coi_expiration_date >= grace_date
                    and today <= self.auto_coi_expiration_date
                )
                or (
                    self.workers_comp_coi_expiration_date >= grace_date
                    and today <= self.workers_comp_coi_expiration_date
                )
            )
        else:
            return False

    @property
    def is_insurance_compliant(self):
        today = datetime.date.today()
        return (
            self.gl_coi_expiration_date is not None
            and self.auto_coi_expiration_date is not None
            and self.workers_comp_coi_expiration_date is not None
            and self.gl_coi_expiration_date > today
            and self.auto_coi_expiration_date > today
            and self.workers_comp_coi_expiration_date > today
        )

    @property
    def is_payout_setup(self):
        return bool(self.stripe_connect_account_id or self.payee_name)

    @property
    def is_tax_compliant(self):
        return bool(self.stripe_connect_account_id and self.w9)

    def pre_save(sender, instance, *args, **kwargs):
        latitude, longitude = geocode_address(
            f"{instance.street} {instance.city} {instance.state} {instance.postal_code}"
        )
        instance.latitude = latitude or 0
        instance.longitude = longitude or 0


pre_save.connect(SellerLocation.pre_save, sender=SellerLocation)
