import random
import string

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_save, post_delete
import threading
import logging

from api.models.order.order import Order
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
        max_length=20, choices=COMPLIANCE_STATUS_CHOICES, default="NOT_REQUIRED"
    )
    tax_exempt_status = models.CharField(
        max_length=20, choices=TaxExemptStatus.choices, default=TaxExemptStatus.NONE
    )

    intercom_id = models.CharField(max_length=255, blank=True, null=True,
                                   help_text="This is the company_id in Intercom.")

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.invoice_frequency and self.invoice_day_of_month:
            raise ValidationError(
                "You cannot set both 'Invoice Frequency' and 'Invoice Day of Month'",
            )

    def post_create(sender, instance, created, **kwargs):
        if created:
            # Generate unique share code.
            share_code = "".join(
                random.choice(string.ascii_uppercase + string.digits) for _ in range(6)
            )
            while share_code in UserGroup.objects.values_list("share_code", flat=True):
                share_code = "".join(
                    random.choice(string.ascii_uppercase + string.digits)
                    for _ in range(6)
                )
            # Save via update so this post_create is not called a second time.
            # instance.share_code = share_code
            # instance.save()
            UserGroup.objects.filter(id=instance.id).update(share_code=share_code)
        # Update Intercom company asynchronously.
        # Note: This is done asynchronously because it is not critical.
        p = threading.Thread(target=instance.intercom_sync)
        p.start()

    @property
    def intercom_custom_attributes(self) -> CustomAttributesType:
        """Return Custome Attributes to sync with Intercom
        """
        custom_attributes = CustomAttributesType({
            "Seller ID": self.seller.id if self.seller else None,
            "Autopay": self.autopay,
            "Net Terms Days": self.net_terms,
            "Invoice Frequency in Days": self.invoice_frequency,
            "Credit Line Amount": float(self.credit_line_limit) if self.credit_line_limit else None,
            "Insurance and Tax Request Status": self.compliance_status,
            "Tax Exempt Status": self.tax_exempt_status,
            "Invoice Day of Month": self.invoice_day_of_month,
            "Project Based Billing": self.invoice_at_project_completion,
            "Share Code": self.share_code,
        })
        return custom_attributes

    def intercom_sync(self):
        """Create or Updates Intercom Company with UserGroup. 
        """
        try:
            # Update or create Company in Intercom
            company = Intercom.Company.update_or_create(
                str(self.id), self.name, custom_attributes=self.intercom_custom_attributes
            )
            if company and self.intercom_id != company["id"]:
                UserGroup.objects.filter(id=self.id).update(intercom_id=company["id"])
            return company
        except Exception as e:
            logger.error(f"UserGroup.intercom_sync: [{e}]", exc_info=e)

    def credit_limit_used(self):
        orders = Order.objects.filter(order_group__user_address__user_group=self)
        total_customer_price = 0.0
        total_paid = 0.0

        # Loop through orders to get total customer price and total paid.
        for order in orders:
            total_customer_price, _, total_paid = order.payment_status()
            total_customer_price += total_customer_price
            total_paid += total_paid

        # Current credit utilization.
        credit_used = total_customer_price - total_paid
        return credit_used

    def post_delete(sender, instance, **kwargs):
        # Delete intercom Company.
        try:
            Intercom.Company.delete(instance.intercom_id)
        except Exception as e:
            logger.error(f"UserGroup.post_delete: [{e}]", exc_info=e)


post_save.connect(UserGroup.post_create, sender=UserGroup)
post_delete.connect(UserGroup.post_delete, sender=UserGroup)
