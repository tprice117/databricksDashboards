import logging
import random
import string
import threading
import datetime
from typing import List

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from api.models.order.order_line_item import OrderLineItem
from api.models.seller.seller import Seller
from api.models.order.order import Order
from common.models import BaseModel
from common.utils.get_file_path import get_file_path
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
    owned_and_rented_equiptment_coi = models.FileField(
        upload_to=get_file_path, blank=True, null=True
    )
    credit_report = models.FileField(upload_to=get_file_path, blank=True, null=True)

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


class CompanyUtils:
    """This class contains utility methods for the Companies. This is used in the Customer Admin Portal."""

    @staticmethod
    def calculate_percentage_change(old_value, new_value):
        if old_value == 0:
            # Handle the case where the old value is 0 to avoid division by zero
            return "Undefined"  # Or handle it in a way that makes sense for your application
        percentage_change = ((new_value - old_value) / old_value) * 100
        return round(percentage_change)

    @staticmethod
    def get_new(search_q: str = None):
        """Get all companies created in the last 30 days."""
        cutoff_date = datetime.date.today() - datetime.timedelta(days=30)
        user_groups = UserGroup.objects.filter(seller__isnull=True)
        if search_q:
            # https://docs.djangoproject.com/en/4.2/topics/db/search/
            user_groups = user_groups.filter(name__icontains=search_q)
        # Get all created in the last 30 days.
        user_groups = user_groups.filter(created_on__gte=cutoff_date)
        user_groups = user_groups.order_by("-created_on")
        return user_groups

    @staticmethod
    def get_active(search_q: str = None) -> List[UserGroup]:
        """Get all active companies.
        This returns all companies that have at least one active order in the last 30 days.
        """
        cutoff_date = datetime.date.today() - datetime.timedelta(days=30)
        # Active Companies is user group on an order within date range (or within last 30 days if no range)
        orders = Order.objects.filter(end_date__gte=cutoff_date)
        if search_q:
            orders = orders.filter(
                order_group__user__user_group__name__icontains=search_q
            )
        orders.select_related("order_group__user__user_group")
        orders = orders.distinct("order_group__user__user_group")
        orders = orders.order_by("order_group__user__user_group", "-end_date")
        user_groups = []
        for order in orders:
            setattr(order.order_group.user.user_group, "last_order", order.end_date)
            user_groups.append(order.order_group.user.user_group)
        # sort based on user_group.created_on
        user_groups = sorted(user_groups, key=lambda x: x.last_order, reverse=True)
        return user_groups

    @staticmethod
    def get_churning(
        search_q: str = None,
        tab: str = None,
        old_date: datetime.date = None,
        new_date: datetime.date = None,
    ) -> List[UserGroup]:
        """Get all churning companies.
        -
        if tab is "fully_churned" then Get all fully churned companies.
        Fully Churned = user group is not an active company within the date range, but was 30 days prior
        to the date range (or within last 30 days if no range)
        -
        if tab is "churning" then Get all churning companies.
        Companies that had orders in the previous 30 day period, but no orders in the last 30 day period.

        return: List of UserGroup objects
        """
        import time

        if old_date is None:
            old_date = datetime.date.today() - datetime.timedelta(days=60)
        if new_date is None:
            new_date = datetime.date.today() - datetime.timedelta(days=30)

        start_time = time.time()
        # Churning = sum of all order.customer total for orders within the date range for a given User Group
        # is less than the sum of the previous date range (or within last 30 days if no range)
        # ie. If I select (1) Today to last Wednesday, it will look from (2) last Wednesday to 2 Wednesdays ago
        # to compare the sums. If the sum of order totals for range 1 is less than range 2. That’s “churning”.
        #
        # Fully Churned = user group is not an active company within the date range, but was 30 days prior
        # to the date range (or within last 30 days if no range)
        orders = Order.objects.filter(end_date__gte=old_date)
        if search_q:
            orders = orders.filter(
                order_group__user__user_group__name__icontains=search_q
            )
        orders.select_related("order_group__user__user_group")
        orders = orders.prefetch_related("order_line_items")
        print(orders.count())
        step_time = time.time()
        print(f"Query count: {step_time - start_time}")
        user_groups_d = {}
        for order in orders:
            ugid = order.order_group.user.user_group_id
            if ugid not in user_groups_d:
                user_groups_d[ugid] = {
                    "count": 1,
                    "count_old": 0,
                    "count_new": 0,
                    "total_old": 0,
                    "total_new": 0,
                    "user_group": order.order_group.user.user_group,
                    "last_order": order.end_date,
                }
            user_groups_d[ugid]["count"] += 1
            if order.end_date < new_date:
                user_groups_d[ugid]["total_old"] += order.customer_price()
                user_groups_d[ugid]["count_old"] += 1
            else:
                user_groups_d[ugid]["total_new"] += order.customer_price()
                user_groups_d[ugid]["count_new"] += 1
            if order.end_date > user_groups_d[ugid]["last_order"]:
                user_groups_d[ugid]["last_order"] = order.end_date
            # if len(user_groups_d) == 10:
            #     break
        step_time = time.time()
        print(f"Loop orders: {step_time - start_time}")

        user_groups = []
        for ugid, data in user_groups_d.items():
            if data["total_old"] > data["total_new"]:
                setattr(data["user_group"], "last_order", data["last_order"])
                setattr(data["user_group"], "count_old", data["count_old"])
                setattr(data["user_group"], "count_new", data["count_new"])
                setattr(
                    data["user_group"],
                    "percent_change",
                    CompanyUtils.calculate_percentage_change(
                        data["total_old"], data["total_new"]
                    ),
                )
                setattr(
                    data["user_group"],
                    "total_spend",
                    data["total_new"] + data["total_old"],
                )
                setattr(
                    data["user_group"],
                    "change",
                    data["total_new"] - data["total_old"],
                )
                if tab == "fully_churned":
                    if data["total_new"] == 0:
                        user_groups.append(data["user_group"])
                else:
                    user_groups.append(data["user_group"])
        step_time = time.time()
        print(f"Filter churning: {step_time - start_time}")
        # Sort by change
        user_groups = sorted(user_groups, key=lambda x: x.change)
        step_time = time.time()
        print(f"Sort: {step_time - start_time}")
        return user_groups
