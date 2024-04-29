import logging
import random
import string
import threading

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from api.models.order.order_line_item import OrderLineItem
from api.models.seller.seller import Seller
from common.models import BaseModel
from communications.intercom.intercom import Intercom
from communications.intercom.typings import CustomAttributesType

logger = logging.getLogger(__name__)


class UserGroup(BaseModel):
    class TaxExemptStatus(models.TextChoices):
        NONE = "none"
        EXEMPT = "exempt"
        REVERSE = "reverse"

    class NetTerms(models.IntegerChoices):
        IMMEDIATELY = 0, "Immediately"
        NET_14 = 14, "Net 14"
        NET_30 = 30, "Net 30"
        NET_45 = 45, "Net 45"
        NET_60 = 60, "Net 60"

    class InvoiceFrequency(models.IntegerChoices):
        IMMEDIATELY = 0, "Immediately"
        WEEKLY = 7, "Weekly"
        BI_WEEKLY = 14, "Bi-Weekly"
        MONTHLY = 30, "Monthly"

    COMPLIANCE_STATUS_CHOICES = (
        ("NOT_REQUIRED", "Not Required"),
        ("REQUESTED", "Requested"),
        ("IN-PROGRESS", "In-Progress"),
        ("NEEDS_REVIEW", "Needs Review"),
        ("APPROVED", "Approved"),
    )

    seller = models.OneToOneField(Seller, models.DO_NOTHING, blank=True, null=True)
    name = models.CharField(max_length=255)
    pay_later = models.BooleanField(default=False)
    # SECTION: Invoicing and Payment
    autopay = models.BooleanField(default=False)
    net_terms = models.IntegerField(
        choices=NetTerms.choices,
        default=NetTerms.IMMEDIATELY,
    )
    invoice_frequency = models.IntegerField(
        choices=InvoiceFrequency.choices,
        default=InvoiceFrequency.IMMEDIATELY,
        blank=True,
        null=True,
    )
    invoice_day_of_month = models.IntegerField(blank=True, null=True)
    invoice_at_project_completion = models.BooleanField(
        default=False,
        help_text="Send invoices when all OrderGroups in a project are completed.",
    )
    # END SECTION: Invoicing and Payment
    is_superuser = models.BooleanField(default=False)
    share_code = models.CharField(max_length=6, blank=True)
    parent_account_id = models.CharField(max_length=255, blank=True, null=True)
    credit_line_limit = models.DecimalField(
        max_digits=18, decimal_places=2, blank=True, null=True
    )
    compliance_status = models.CharField(
        max_length=20,
        choices=COMPLIANCE_STATUS_CHOICES,
        default="NOT_REQUIRED",
    )
    tax_exempt_status = models.CharField(
        max_length=20,
        choices=TaxExemptStatus.choices,
        default=TaxExemptStatus.NONE,
    )

    intercom_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="This is the company_id in Intercom.",
    )

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.invoice_frequency and self.invoice_day_of_month:
            raise ValidationError(
                "You cannot set both 'Invoice Frequency' and 'Invoice Day of Month'",
            )

    def post_create(sender, instance, created, **kwargs):
        # Update Intercom company asynchronously.
        # Note: This is done asynchronously because it is not critical.
        p = threading.Thread(target=instance.intercom_sync)
        p.start()

    @property
    def intercom_custom_attributes(self) -> CustomAttributesType:
        """Return Custome Attributes to sync with Intercom"""
        custom_attributes = CustomAttributesType(
            {
                "Seller ID": str(self.seller.id) if self.seller else None,
                "Autopay": self.autopay,
                "Net Terms Days": self.net_terms,
                "Invoice Frequency in Days": self.invoice_frequency,
                "Credit Line Amount": (
                    float(self.credit_line_limit) if self.credit_line_limit else None
                ),
                "Insurance and Tax Request Status": self.compliance_status,
                "Tax Exempt Status": self.tax_exempt_status,
                "Invoice Day of Month": self.invoice_day_of_month,
                "Project Based Billing": self.invoice_at_project_completion,
                "Share Code": self.share_code,
            }
        )
        return custom_attributes

    def intercom_sync(self):
        """Create or Updates Intercom Company with UserGroup."""
        try:
            # Update or create Company in Intercom
            company = Intercom.Company.update_or_create(
                str(self.id),
                self.name,
                custom_attributes=self.intercom_custom_attributes,
            )
            if company and self.intercom_id != company["id"]:
                UserGroup.objects.filter(id=self.id).update(intercom_id=company["id"])
            return company
        except Exception as e:
            logger.error(f"UserGroup.intercom_sync: [{e}]", exc_info=e)

    def credit_limit_used(self):
        order_line_items = OrderLineItem.objects.filter(
            order__order_group__user_address__user_group=self, paid=False
        )
        credit_used = 0
        for order_line_item in order_line_items:
            credit_used += order_line_item.customer_price()
        return credit_used

    def post_delete(sender, instance, **kwargs):
        # Delete intercom Company.
        try:
            Intercom.Company.delete(instance.intercom_id)
        except Exception as e:
            logger.error(f"UserGroup.post_delete: [{e}]", exc_info=e)


post_save.connect(UserGroup.post_create, sender=UserGroup)
post_delete.connect(UserGroup.post_delete, sender=UserGroup)


@receiver(pre_save, sender=UserGroup)
def status_changed(sender, instance: UserGroup, *args, **kwargs):
    db_instance = UserGroup.objects.filter(id=instance.id).first()

    if not db_instance:
        # If the instance is being created, generate a share code.
        instance.share_code = "".join(
            random.choice(string.ascii_uppercase + string.digits) for _ in range(6)
        )
        while instance.share_code in UserGroup.objects.values_list(
            "share_code", flat=True
        ):
            instance.share_code = "".join(
                random.choice(string.ascii_uppercase + string.digits) for _ in range(6)
            )
