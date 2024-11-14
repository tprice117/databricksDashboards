import logging
from decimal import Decimal
from functools import lru_cache
from typing import List, Optional

import mailchimp_transactional as MailchimpTransactional
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from api.models.disposal_location.disposal_location import DisposalLocation
from api.models.order.order_line_item import OrderLineItem
from api.models.order.order_line_item_type import OrderLineItemType
from api.models.track_data import track_data
from api.models.waste_type import WasteType
from api.utils.auth0 import get_password_change_url, get_user_data
from api.utils.utils import encrypt_string
from billing.models import Invoice
from common.models import BaseModel
from common.models.choices.approval_status import ApprovalStatus
from common.models.choices.user_type import UserType
from common.utils.generate_code import save_unique_code
from common.utils.stripe.stripe_utils import StripeUtils
from communications.intercom.conversation import Conversation as IntercomConversation
from notifications import signals as notifications_signals
from notifications.utils.add_email_to_queue import (
    add_email_to_queue,
    add_internal_email_to_queue,
)

logger = logging.getLogger(__name__)

mailchimp = MailchimpTransactional.Client(settings.MAILCHIMP_API_KEY)

USER_MODEL = None
USER_SELLER_LOCATION_MODEL = None
ORDER_APPROVAL_MODEL = None
PRICING_LINE_ITEM_MODEL = None
PRICING_LINE_ITEM_GROUP_MODEL = None
PRICING_ENGINE_RESPONSE_SERIALIZER = None


def get_our_user_model():
    """This imports the User model.
    This avoid the circular import issue."""
    global USER_MODEL
    if USER_MODEL is None:
        from api.models.user.user import User as USER_MODEL

    return USER_MODEL


def get_user_seller_location_model():
    """This imports the UserSellerLocation model.
    This avoid the circular import issue."""
    global USER_SELLER_LOCATION_MODEL
    if USER_SELLER_LOCATION_MODEL is None:
        from api.models.user.user_seller_location import (
            UserSellerLocation as USER_SELLER_LOCATION_MODEL,
        )

    return USER_SELLER_LOCATION_MODEL


def get_order_approval_model():
    """This imports the OrderGroupAdminApprovalOrder model.
    This avoid the circular import issue."""
    global ORDER_APPROVAL_MODEL
    if ORDER_APPROVAL_MODEL is None:
        from admin_approvals.models import (
            UserGroupAdminApprovalOrder as ORDER_APPROVAL_MODEL,
        )

    return ORDER_APPROVAL_MODEL


def get_pricing_line_item_model():
    """This imports the PricingLineItem model.
    This avoid the circular import issue."""
    global PRICING_LINE_ITEM_MODEL
    if PRICING_LINE_ITEM_MODEL is None:
        from pricing_engine.models import PricingLineItem as PRICING_LINE_ITEM_MODEL

    return PRICING_LINE_ITEM_MODEL


def get_pricing_line_item_group_model():
    """This imports the PricingLineItemGroup model.
    This avoid the circular import issue."""
    global PRICING_LINE_ITEM_GROUP_MODEL
    if PRICING_LINE_ITEM_GROUP_MODEL is None:
        from pricing_engine.models import (
            PricingLineItemGroup as PRICING_LINE_ITEM_GROUP_MODEL,
        )

    return PRICING_LINE_ITEM_GROUP_MODEL


def get_pricing_engine_response_serializer():
    """This imports the PricingLineItemGroup model.
    This avoid the circular import issue."""
    global PRICING_ENGINE_RESPONSE_SERIALIZER
    if PRICING_ENGINE_RESPONSE_SERIALIZER is None:
        from pricing_engine.api.v1.serializers.response.pricing_engine_response import (
            PricingEngineResponseSerializer as PRICING_ENGINE_RESPONSE_SERIALIZER,
        )

    return PRICING_ENGINE_RESPONSE_SERIALIZER


@track_data(
    "submitted_on",
    "start_date",
    "end_date",
    "schedule_details",
    "schedule_window",
    "status",
)
class Order(BaseModel):
    class Type(models.TextChoices):
        DELIVERY = "DELIVERY"
        SWAP = "SWAP"
        REMOVAL = "REMOVAL"
        AUTO_RENEWAL = "AUTO_RENEWAL"
        ONE_TIME = "ONE_TIME"

    class Status(models.TextChoices):
        ADMIN_APPROVAL_PENDING = "ADMIN_APPROVAL_PENDING"
        ADMIN_APPROVAL_DECLINED = "ADMIN_APPROVAL_DECLINED"
        PENDING = ("PENDING", "Supplier confirmation pending")
        SCHEDULED = "SCHEDULED"
        CANCELLED = "CANCELLED"
        COMPLETE = "COMPLETE"
        CREDIT_APPLICATION_APPROVAL_PENDING = "CREDIT_APPLICATION_APPROVAL_PENDING"
        CREDIT_APPLICATION_DECLINED = "CREDIT_APPLICATION_DECLINED"
        NO_PAYMENT_METHOD = "NO_PAYMENT_METHOD"

    order_group = models.ForeignKey(
        "api.OrderGroup", models.PROTECT, related_name="orders"
    )
    disposal_location = models.ForeignKey(
        DisposalLocation, models.DO_NOTHING, blank=True, null=True
    )
    start_date = models.DateField()
    end_date = models.DateField()
    submitted_on = models.DateTimeField(blank=True, null=True)
    submitted_by = models.ForeignKey(
        "api.User",
        models.SET_NULL,
        related_name="submitted_orders",
        blank=True,
        null=True,
    )
    accepted_on = models.DateTimeField(blank=True, null=True)
    accepted_by = models.ForeignKey(
        "api.User",
        models.SET_NULL,
        related_name="accepted_orders",
        blank=True,
        null=True,
    )
    completed_on = models.DateTimeField(blank=True, null=True)
    completed_by = models.ForeignKey(
        "api.User",
        models.SET_NULL,
        related_name="completed_orders",
        blank=True,
        null=True,
    )
    schedule_details = models.TextField(
        blank=True, null=True
    )  # 6.6.23 (Modified name to schedule_details from additional_schedule_details)
    status = models.CharField(
        max_length=50,
        choices=Status.choices,
        default=Status.PENDING,
    )
    # https://developers.intercom.com/docs/build-an-integration/learn-more/rest-apis/identifiers-and-urls/
    intercom_id = models.CharField(
        max_length=128,
        blank=True,
        null=True,
        help_text="Conversation between Seller and Admin.",
    )
    custmer_intercom_id = models.CharField(
        max_length=128,
        blank=True,
        null=True,
        help_text="Conversation between Seller and Customer.",
    )
    billing_comments_internal_use = models.TextField(blank=True, null=True)  # 6.6.23
    schedule_window = models.CharField(
        max_length=35,
        choices=[
            ("Anytime (7am-4pm)", "Anytime (7am-4pm)"),
            ("Morning (7am-11am)", "Morning (7am-11am)"),
            ("Afternoon (12pm-4pm)", "Afternoon (12pm-4pm)"),
            # Deprecated, do not show in UI. This is so old data can still be read.
            ("Evening (5pm-8pm)", "Evening (5pm-8pm)"),
        ],
        blank=True,
        null=True,
    )  # 6.6.23
    checkout_order = models.ForeignKey(
        "cart.CheckoutOrder",
        models.SET_NULL,
        related_name="orders",
        blank=True,
        null=True,
    )
    code = models.CharField(
        max_length=8,
        unique=True,
        blank=True,
        null=True,
        help_text="Unique code for the Transaction.",
    )

    class Meta:
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"

    @property
    def is_past_due(self):
        """Returns True if the Order is past due (end date is <= today), False otherwise.
        NOTE: Maybe should add a bit of fudge due to timezone differences."""
        return self.end_date <= timezone.now().date()

    @property
    def order_type(self):
        return self.get_order_type()

    @property
    def get_code(self):
        return f"T-{self.code}"

    def update_status_on_credit_application_approved(self):
        """Update the Order status after the UserGroupCreditApplication is approved."""
        self.status = Order.Status.PENDING
        if hasattr(self, "user_group_admin_approval_order"):
            # Check for any Admin Policy checks.
            if self.user_group_admin_approval_order.status == ApprovalStatus.PENDING:
                self.status = Order.Status.ADMIN_APPROVAL_PENDING
            elif self.user_group_admin_approval_order.status == ApprovalStatus.DECLINED:
                self.status = Order.Status.ADMIN_APPROVAL_DECLINED
        self.save()

    def update_status_on_credit_application_declined(self):
        """Update the Order status after the UserGroupCreditApplication is declined."""
        self.submitted_on = None
        self.status = Order.Status.PENDING
        self.save()

    @property
    def requires_terms_agreement(self):
        if (
            self.order_type == Order.Type.DELIVERY
            or self.order_type == Order.Type.ONE_TIME
        ):
            return True
        return False

    @property
    def seller_accept_order_url(self):
        return f"{settings.API_URL}/api/order/{self.id}/accept/?key={encrypt_string(str(self.id))}"

    @property
    def seller_view_order_url(self):
        return f"{settings.API_URL}/api/order/{self.id}/view/?key={encrypt_string(str(self.id))}"

    @lru_cache(maxsize=10)  # Do not recalculate this for the same object.
    def seller_price(self):
        seller_price = sum(
            [
                order_line_item.seller_payout_price()
                for order_line_item in self.order_line_items.all()
            ]
        )
        return round(seller_price, 2)

    @lru_cache(maxsize=10)  # Do not recalculate this for the same object.
    def customer_price(self):
        return sum(
            [
                order_line_item.customer_price()
                for order_line_item in self.order_line_items.all()
            ]
        )

    def full_price(self):
        default_take_rate = (
            self.order_group.seller_product_seller_location.seller_product.product.main_product.default_take_rate
        )
        return self.seller_price() * (1 + (default_take_rate / 100))

    @property
    def take_rate(self):
        seller_price = self.seller_price()
        customer_price = self.customer_price()
        if seller_price == 0:
            return 0
        return round(((customer_price - seller_price) / seller_price) * 100, 2)

    def total_paid_to_seller(self):
        total_paid_to_seller = sum([payout.amount for payout in self.payouts.all()])
        return round(total_paid_to_seller, 2)

    def needed_payout_to_seller(self):
        return round(self.seller_price() - self.total_paid_to_seller(), 2)

    def stripe_invoice_summary_item_description(self):
        """Create a description for the Stripe Invoice Summary Item.
        Create one of old style and one of new style because we need to check if
        Stripe Invoice Summary Item exists for the old description already and only
        create new Invoice Summary Items using the new style.
        Return a tuple with the old style and new style descriptions.
        Description is the old style description.
        Description2 adds the project_id, from OrderGroup or UserAddress to the description.

        Returns:
            tuple(str, str): Orignal description and new expaned description (could be exactly the same).
        """
        description = f'{self.order_group.seller_product_seller_location.seller_product.product.main_product.name} | {self.start_date.strftime("%a, %b %-d")} - {self.end_date.strftime("%a, %b %-d")} | {self.order_type}'
        description2 = description
        if self.order_group.project_id:
            description2 = f"{description2} | {self.order_group.project_id}"
        elif self.order_group.user_address.project_id:
            description2 = f"{description2} | {self.order_group.project_id}"
        description = f"{description} | {str(self.id)[:5]}"
        description2 = f"{description2} | {str(self.id)[:5]}"
        return description, description2

    def get_order_type(self):
        # Pre-calculate conditions
        first_order = self.order_group.orders.order_by("created_on").first()
        is_first_order = str(first_order.id) == str(self.id)
        order_start_end_equal = self.start_date == self.end_date
        order_group_start_equal = self.start_date == self.order_group.start_date
        order_group_end_equal = self.end_date == self.order_group.end_date
        auto_renews = (
            self.order_group.seller_product_seller_location.seller_product.product.main_product.auto_renews
        )
        order_count = Order.objects.filter(order_group=self.order_group).count()
        one_day_rental = self.order_group.start_date == self.order_group.end_date

        # Check order types in order of precedence
        if (
            order_group_start_equal
            and order_start_end_equal
            and (
                not order_group_end_equal
                or (order_group_end_equal and not one_day_rental)
            )
            and is_first_order
        ):
            return Order.Type.DELIVERY
        elif (
            order_count == 1
            and order_group_start_equal
            and order_group_end_equal
            and not auto_renews
        ):
            return Order.Type.ONE_TIME
        elif order_group_end_equal and order_count > 1:
            if is_first_order:
                return Order.Type.DELIVERY
            return Order.Type.REMOVAL
        elif order_count > 1 and not order_group_end_equal and not auto_renews:
            return Order.Type.SWAP
        elif auto_renews:
            return Order.Type.AUTO_RENEWAL
        else:
            return None

    def all_order_line_items_invoiced(self: "Order"):
        return all(
            [
                order_line_item.payment_status()
                in [
                    OrderLineItem.PaymentStatus.INVOICED,
                    OrderLineItem.PaymentStatus.PAID,
                ]
                for order_line_item in self.order_line_items.all()
            ]
        )

    def payment_status(self):
        total_customer_price = 0
        total_invoiced = 0
        total_paid = 0

        order_line_item: OrderLineItem
        for order_line_item in self.order_line_items.all():
            payment_status = order_line_item.payment_status()

            # Define variables for payment status.
            is_invoiced = (
                payment_status == OrderLineItem.PaymentStatus.INVOICED
                or payment_status == OrderLineItem.PaymentStatus.PAID
            )
            is_paid = payment_status == OrderLineItem.PaymentStatus.PAID

            total_customer_price += order_line_item.customer_price()
            total_invoiced += order_line_item.customer_price() if is_invoiced else 0
            total_paid += order_line_item.customer_price() if is_paid else 0

        # Return (total_customer_price, total_invoiced, total_paid).
        return total_customer_price, total_invoiced, total_paid

    def get_invoices(self) -> List[Invoice]:
        """Return all the invoices for this Order."""
        inv_resp = []
        stripe_invoice_ids = []
        for order_line_item in self.order_line_items.all():
            if order_line_item.stripe_invoice_line_item_id:
                try:
                    invoice_line_item = StripeUtils.InvoiceItem.get(
                        order_line_item.stripe_invoice_line_item_id
                    )
                    stripe_invoice_ids.append(invoice_line_item.invoice)
                except Exception as e:
                    logger.error(
                        f"order_line_item.id:{order_line_item.id} stripe_invoice_line_item_id:{order_line_item.stripe_invoice_line_item_id} does not exist. [{e}]",
                        exc_info=e,
                    )

        stripe_invoice_ids = list(set(stripe_invoice_ids))

        if stripe_invoice_ids:
            invoice_objs = Invoice.objects.filter(invoice_id__in=stripe_invoice_ids)
            for inv in invoice_objs:
                inv_resp.append(inv)

        return inv_resp

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def clean(self):
        super().clean()

        # Ensure submitted_on is not NULL if status is not PENDING.
        if self.status != Order.Status.PENDING and not self.submitted_on:
            raise ValidationError(
                "Submitted On (which means Order has been checked out) must be set if status is not PENDING"
            )
        # Ensure end_date is on or after start_date.
        if self.start_date > self.end_date:
            raise ValidationError("Start date must be on or before end date")
        # Ensure start_date is on or after OrderGroup start_date.
        elif self.start_date < self.order_group.start_date:
            raise ValidationError(
                "Start date must be on or after OrderGroup start date"
            )
        # Ensure end_date is on or before OrderGroup end_date.
        elif self.order_group.end_date and self.end_date > self.order_group.end_date:
            raise ValidationError("End date must be on or before OrderGroup end date")
        # Ensure this Order doesn't overlap with any other Orders for this OrderGroup.
        elif (
            self._state.adding
            and Order.objects.filter(
                order_group=self.order_group,
                start_date__lt=self.end_date,
                end_date__gt=self.start_date,
            )
            .exclude(id=self.id)
            .exists()
        ):
            raise ValidationError(
                "This Order overlaps with another Order for this OrderGroup"
            )

    def add_line_items(self, created):
        order_line_items = OrderLineItem.objects.filter(order=self)
        # if self.submitted_on_has_changed and order_line_items.count() == 0:
        if created and order_line_items.count() == 0:
            try:
                # Only add OrderLineItems if this is the first Order in the OrderGroup.
                order_group_orders = Order.objects.filter(order_group=self.order_group)

                # Create list of OrderLineItems for this Order to be created.
                new_order_line_items: List[OrderLineItem] = []

                is_first_order = (
                    self.order_group.start_date == self.start_date
                    and order_group_orders.count() == 1
                )

                is_last_order = (
                    self.order_group.end_date == self.end_date
                    and order_group_orders.count() > 1
                )

                is_equiptment_order = (
                    self.order_group.seller_product_seller_location.seller_product.product.main_product.has_rental_multi_step
                )

                delivery_fee = 0
                if is_first_order:
                    new_order_line_items.extend(
                        self._add_order_line_item_delivery(),
                    )
                    if (
                        self.order_group.seller_product_seller_location.delivery_fee
                        is not None
                    ):
                        delivery_fee = (
                            self.order_group.seller_product_seller_location.delivery_fee
                        )

                # NOTE: Don't add any other OrderLineItems if this is a non equipment removal.
                standard_removal = is_last_order and not is_equiptment_order
                # Add Removal Line Item for first and last Order.
                # The first order will get any actual removal fee, the last order will get a $0 removal line item.
                if is_first_order:
                    new_order_line_items.extend(self._add_order_line_item_removal())
                elif is_last_order:
                    new_order_line_items.extend(
                        self._add_order_line_item_removal(add_empty=True)
                    )

                # If the OrderGroup has Material, add those line items.
                if not standard_removal and hasattr(self.order_group, "material"):
                    new_order_line_items.extend(
                        self.order_group.material.order_line_items(
                            self,
                        )
                    )

                # If the OrderGroup has Rental One-Step, add those line items. e.g. Porta Potty
                # Never add Rental One-Step line items for the last Order, they are added at the beginning.
                if not is_last_order and hasattr(self.order_group, "rental_one_step"):
                    new_order_line_items.extend(
                        self.order_group.rental_one_step.order_line_items(self)
                    )

                # If the OrderGroup has Rental Two-Step (Legacy), add those line items. e.g. Roll Off Dumpster
                # If this is a removal, then do not include the included days line item.
                if hasattr(self.order_group, "rental"):
                    new_order_line_items.extend(
                        self.order_group.rental.order_line_items(
                            self, is_last_order=is_last_order
                        )
                    )

                # If the OrderGroup has Rental Multi-Step, add those line items.
                # NOTE: Do not add Rental Multi-Step line items for the first Order. e.g. Telehandler
                if (
                    hasattr(self.order_group, "rental_multi_step")
                    and not is_first_order
                ):
                    new_order_line_items.extend(
                        self.order_group.rental_multi_step.order_line_items(self)
                    )

                # If the OrderGroup has Service, add those line items.
                if hasattr(self.order_group, "service") and not is_last_order:
                    new_order_line_items.extend(
                        self.order_group.service.order_line_items(self)
                    )

                # If the OrderGroup has ServiceTimesPerWeek, add those line items.
                if not standard_removal and hasattr(
                    self.order_group, "service_times_per_week"
                ):
                    new_order_line_items.extend(
                        self.order_group.service_times_per_week.order_line_items(self)
                    )

                # For all the OrderLineItems, compute the Fuel and Environmental Fee.
                new_order_line_items.extend(
                    self._add_fuel_and_environmental(new_order_line_items),
                )

                if new_order_line_items:
                    # Get taxes, but only if this Transaction is more than $0.
                    get_taxes = False
                    for line_item in new_order_line_items:
                        if line_item.customer_price() > 0:
                            get_taxes = True
                            break
                    if get_taxes:
                        StripeUtils.PriceCalculation.calculate_price_details(
                            self, new_order_line_items, float(delivery_fee)
                        )
                    else:
                        # Set to 0 to denote that taxes are not needed.
                        for line_item in new_order_line_items:
                            line_item.tax = 0
                    OrderLineItem.objects.bulk_create(new_order_line_items)

                # Check for any Admin Policy checks.
                self.admin_policy_checks(orders=order_group_orders)
            except Exception as e:
                logger.error(f"Order.post_save: [{self.id}]-[{e}]", exc_info=e)

    def _add_order_line_item_delivery(self) -> Optional[List[OrderLineItem]]:
        return (
            [
                OrderLineItem(
                    order=self,
                    order_line_item_type=OrderLineItemType.objects.get(code="DELIVERY"),
                    rate=self.order_group.seller_product_seller_location.delivery_fee,
                    quantity=1,
                    description="Delivery Fee",
                    platform_fee_percent=self.order_group.take_rate,
                    is_flat_rate=True,
                )
            ]
            if self.order_group.seller_product_seller_location.delivery_fee is not None
            else []
        )

    def _add_order_line_item_removal(
        self, add_empty=False
    ) -> Optional[List[OrderLineItem]]:
        if add_empty:
            return [
                OrderLineItem(
                    order=self,
                    order_line_item_type=OrderLineItemType.objects.get(code="REMOVAL"),
                    rate=0,
                    quantity=1,
                    description="Removal Fee",
                    platform_fee_percent=self.order_group.take_rate,
                    is_flat_rate=True,
                )
            ]
        elif self.order_group.seller_product_seller_location.removal_fee:
            return [
                OrderLineItem(
                    order=self,
                    order_line_item_type=OrderLineItemType.objects.get(code="REMOVAL"),
                    rate=self.order_group.seller_product_seller_location.removal_fee,
                    quantity=1,
                    description="Removal Fee",
                    platform_fee_percent=self.order_group.take_rate,
                    is_flat_rate=True,
                )
            ]
        else:
            return []

    def _add_fuel_and_environmental(
        self,
        order_line_items: List[OrderLineItem],
    ) -> Optional[OrderLineItem]:
        order_line_item_type = OrderLineItemType.objects.get(code="FUEL_AND_ENV")

        order_line_items_total = sum(
            [
                float(order_line_item.rate) * float(order_line_item.quantity or 1)
                for order_line_item in order_line_items
            ]
        )

        # If SellerProductSellerLocation has a Fuel and Environmental Fee, multiply
        # it by the total of all OrderLineItems.
        fuel_and_environmental_multiplier = (
            self.order_group.seller_product_seller_location.fuel_environmental_markup
            / 100
            if self.order_group.seller_product_seller_location.fuel_environmental_markup
            else None
        )

        # Calculate the Fuel and Environmental Fee or set it to None.
        fuel_and_environmental_fee = (
            order_line_items_total * float(fuel_and_environmental_multiplier)
            if fuel_and_environmental_multiplier
            else None
        )

        return (
            [
                OrderLineItem(
                    order=self,
                    order_line_item_type=order_line_item_type,
                    rate=Decimal(fuel_and_environmental_fee),
                    quantity=1,
                    description="Fuel and Environmental Fee",
                    platform_fee_percent=self.order_group.take_rate,
                    is_flat_rate=True,
                )
            ]
            if fuel_and_environmental_fee
            else []
        )

    def generate_code(self):
        """Generate a unique code for the Transaction, if code is None."""
        if self.code is None:
            save_unique_code(self)

    @staticmethod
    def post_save(sender, instance: "Order", created, **kwargs):
        if instance.code is None:
            instance.generate_code()

        instance.add_line_items(created)
        notifications_signals.on_order_post_save(sender, instance, created, **kwargs)

    def admin_policy_checks(self, orders=None):
        """Check if Order violates any Admin Policies and sets the Order status to Approval if necessary.

        Args:
            orders (Iterable, Orders): An iterable of Orders to use for policy time period.
                                       Defaults to all orders in order group since the first day of current month.
        """
        # Add policy checks for UserGroupPolicyMonthlyLimit and UserGroupPolicyPurchaseApproval.
        try:
            user = self.order_group.user
            # Admins are not subject to Order Approvals.
            if user.type != UserType.ADMIN:
                orders = (
                    Order.objects.filter(order_group=self.order_group)
                    if orders is None
                    else orders
                )
                # Add policy checks for UserGroupPolicyMonthlyLimit and UserGroupPolicyPurchaseApproval.
                # TODO: Could add policy reason field to Order (this could simply be the db model and/or name of the policy).
                # Get all Orders for this UserGroup this month.
                first_day_of_current_month = timezone.now().replace(day=1)
                orders_this_month = []
                for order in orders:
                    if (
                        order.submitted_on
                        and order.submitted_on >= first_day_of_current_month
                    ):
                        orders_this_month.append(order)

                # Calculate the total of all Orders for this UserGroup this month.
                order_total_this_month = sum(
                    [order.customer_price() for order in orders_this_month]
                )

                # Check that UserGroupPolicyMonthlyLimit will not be exceeded with
                # this Order.
                if hasattr(
                    self.order_group.user_address.user_group, "policy_monthly_limit"
                ) and (
                    order_total_this_month + self.customer_price()
                    > self.order_group.user_address.user_group.policy_monthly_limit.amount
                ):
                    # Set Order status to Approval so that it is returned in api.
                    self.status = Order.Status.ADMIN_APPROVAL_PENDING
                    Order.objects.filter(id=self.id).update(
                        status=Order.Status.ADMIN_APPROVAL_PENDING
                    )
                    get_order_approval_model().objects.create(order_id=self.id)
                    # raise ValidationError(
                    #     "Monthly Order Limit has been exceeded. This Order will be sent to your Admin for approval."
                    # )
                # Check that UserGroupPolicyPurchaseApproval will not be exceeded with this Order.
                elif hasattr(
                    self.order_group.user_address.user_group,
                    "policy_purchase_approvals",
                ):
                    user_group_purchase_approval = self.order_group.user_address.user_group.policy_purchase_approvals.filter(
                        user_type=user.type
                    ).first()
                    if (
                        user_group_purchase_approval
                        and self.customer_price() > user_group_purchase_approval.amount
                    ):
                        # Set Order status to Approval so that it is returned in api.
                        self.status = Order.Status.ADMIN_APPROVAL_PENDING
                        Order.objects.filter(id=self.id).update(
                            status=Order.Status.ADMIN_APPROVAL_PENDING
                        )
                        get_order_approval_model().objects.create(order_id=self.id)
                        # raise ValidationError(
                        #     "Purchase Approval Limit has been exceeded. This Order will be sent to your Admin for approval."
                        # )
        except Exception as e:
            logger.error(f"Order.admin_policy_checks: [{self.id}]-[{e}]", exc_info=e)

    def send_internal_order_confirmation_email(self):
        # Send email to internal team. Only on our PROD environment.
        if settings.ENVIRONMENT == "TEST":
            try:
                waste_type_str = "Not specified"
                if self.order_group.waste_type:
                    waste_type_str = self.order_group.waste_type.name
                material_tonnage_str = "N/A"
                if getattr(self.order_group, "material", None):
                    material_tonnage_str = self.order_group.material.tonnage_included
                rental_included_days = 0
                if getattr(self.order_group, "rental", None):
                    rental_included_days = self.order_group.rental.included_days

                mailchimp.messages.send(
                    {
                        "message": {
                            "headers": {
                                "reply-to": "dispatch@trydownstream.com",
                            },
                            "from_name": "Downstream",
                            "from_email": "dispatch@trydownstream.com",
                            "to": [{"email": "dispatch@trydownstream.com"}],
                            "subject": "Order Confirmed",
                            "track_opens": True,
                            "track_clicks": True,
                            "html": render_to_string(
                                "order-submission-email.html",
                                {
                                    "orderId": self.id,
                                    "seller": self.order_group.seller_product_seller_location.seller_location.seller.name,
                                    "sellerLocation": self.order_group.seller_product_seller_location.seller_location.name,
                                    "mainProduct": self.order_group.seller_product_seller_location.seller_product.product.main_product.name,
                                    "bookingType": self.order_type,
                                    "wasteType": waste_type_str,
                                    "supplierTonsIncluded": material_tonnage_str,
                                    "supplierRentalDaysIncluded": rental_included_days,
                                    "serviceDate": self.end_date,
                                    "timeWindow": self.schedule_window,
                                    "locationAddress": self.order_group.user_address.street,
                                    "locationCity": self.order_group.user_address.city,
                                    "locationState": self.order_group.user_address.state,
                                    "locationZip": self.order_group.user_address.postal_code,
                                    "locationDetails": self.order_group.access_details,
                                    "additionalDetails": self.order_group.placement_details,
                                },
                            ),
                        }
                    }
                )
            except Exception as e:
                logger.error(
                    f"Order.send_internal_order_confirmation_email: [{self.id}]-[{e}]",
                    exc_info=e,
                )

    def send_customer_email_when_order_scheduled(self):
        # Send email to customer when order is scheduled. Only on our PROD environment.
        if (
            settings.ENVIRONMENT == "TEST"
            and self.order_type != Order.Type.AUTO_RENEWAL
        ):
            try:
                auth0_user = get_user_data(self.order_group.user.user_id)

                try:
                    call_to_action_url = (
                        get_password_change_url(self.order_group.user.user_id)
                        if not auth0_user["email_verified"]
                        else "https://app.trydownstream.com/orders"
                    )
                except Exception as e:
                    call_to_action_url = "https://app.trydownstream.com/orders"
                    logger.warning(
                        f"Order.send_customer_email_when_order_scheduled: [Use default: {call_to_action_url}]-auth0_user:[{auth0_user}]-[{e}]",
                        exc_info=e,
                    )

                # Order status changed
                subject = (
                    "Downstream | Order Confirmed | "
                    + self.order_group.user_address.formatted_address()
                )
                payload = {"order": self, "accept_url": call_to_action_url}
                html_content = render_to_string(
                    "notifications/emails/order-confirmed-email.min.html", payload
                )
                add_email_to_queue(
                    from_email="dispatch@trydownstream.com",
                    to_emails=[self.order_group.user.email],
                    subject=subject,
                    html_content=html_content,
                    reply_to="dispatch@trydownstream.com",
                )
            except Exception as e:
                logger.error(
                    f"Order.send_customer_email_when_order_scheduled: [{self.id}]-[{e}]",
                    exc_info=e,
                )

    def log_order_state(self):
        # Log the Order state.
        # This is used to debug order_type None issues.
        try:
            first_order = self.order_group.orders.order_by("created_on").first()
            is_first_order = first_order.id == self.id
            order_start_end_equal = self.start_date == self.end_date
            order_group_start_equal = self.start_date == self.order_group.start_date
            order_group_end_equal = self.end_date == self.order_group.end_date
            has_subscription = hasattr(self.order_group, "subscription")
            order_count = Order.objects.filter(order_group=self.order_group).count()

            logger.warning(
                f"""Order.log_order_state: [{self.id}]
                -[is_first_order:{is_first_order}]-[first_order.id:{first_order.id}:{type(first_order.id)}]-[self.id:{self.id}:{type(self.id)}]
                -[first_order_id:{first_order.id}]-[order_start_end_equal:{order_start_end_equal}]
                -[order_start_end_equal:{order_start_end_equal}]
                -[order_group_start_equal:{order_group_start_equal}]-[order_group_end_equal:{order_group_end_equal}]
                -[has_subscription:{has_subscription}]-[order_count:{order_count}]
                -[status:{self.status}]-[start_date:{self.start_date}]-[end_date:{self.end_date}]
                -[order_group.start_date:{self.order_group.start_date}]
                -[order_group.end_date:{self.order_group.end_date}]"""
            )
        except Exception as e:
            logger.error(f"Order.log_order_state: [{self.id}]-[{e}]", exc_info=e)

    def send_supplier_approval_email(self):
        # Send email to supplier. Only CC on our PROD environment.
        bcc_emails = []
        if settings.ENVIRONMENT == "TEST":
            bcc_emails.append("dispatch@trydownstream.com")

        try:
            if self.order_type is None:
                self.log_order_state()
            is_first_order = (
                self.order_group.orders.order_by("created_on").first().id == self.id
            )
            if self.order_type != Order.Type.AUTO_RENEWAL or (
                is_first_order and self.order_type == Order.Type.AUTO_RENEWAL
            ):
                # If order type is none, then do not include it in the email.
                # NOTE: If this subject line is changed, then also update
                # supplier_dashboard.views.intercom_new_conversation_webhook to correctly identify this email.
                subject_supplier = f"🚀 Yippee! New {self.order_type} Downstream Booking Landed! [{self.order_group.user_address.formatted_address()}]-[{str(self.id)}]"
                if self.order_type is None:
                    subject_supplier = f"🚀 Yippee! New Downstream Booking Landed! [{self.order_group.user_address.formatted_address()}]-[{str(self.id)}]"
                # The accept button redirects to our server, which will decrypt order_id to ensure it origniated from us,
                # then it opens the order html to allow them to select order status.
                accept_url = f"{settings.DASHBOARD_BASE_URL}{reverse('supplier_booking_detail', kwargs={'order_id': self.id})}"
                html_content_supplier = render_to_string(
                    "notifications/emails/supplier_email.min.html",
                    {"order": self, "accept_url": accept_url, "is_email": True},
                )
                user_seller_locations = (
                    get_user_seller_location_model()
                    .objects.filter(
                        seller_location_id=self.order_group.seller_product_seller_location.seller_location.id
                    )
                    .select_related("user")
                )
                # Get all emails for this seller_location_id.
                # Ensure all emails are non empty and unique.
                to_emails = []
                if (
                    self.order_group.seller_product_seller_location.seller_location.order_email
                ):
                    to_emails.append(
                        self.order_group.seller_product_seller_location.seller_location.order_email
                    )
                for user_seller_location in user_seller_locations:
                    if (
                        user_seller_location.user.email
                        and user_seller_location.user.email not in to_emails
                    ):
                        to_emails.append(user_seller_location.user.email)
                # If no emails found, then send to internal team and log error.
                if not to_emails:
                    logger.error(
                        f"Order.send_supplier_approval_email: no emails found for seller_location_id:[{self.order_group.seller_product_seller_location.seller_location.id}]-[{self.order_group.user_address.formatted_address()}]-[order_id:{str(self.id)}]"
                    )
                    subject_supplier = f"{subject_supplier} - No emails found!"
                    add_internal_email_to_queue(
                        from_email="dispatch@trydownstream.com",
                        subject=subject_supplier,
                        html_content=html_content_supplier,
                        additional_to_emails=[
                            "mwickey@trydownstream.com",
                        ],
                        bcc_emails=bcc_emails,
                        reply_to="dispatch@trydownstream.com",
                    )
                else:
                    add_email_to_queue(
                        from_email="dispatch@trydownstream.com",
                        to_emails=to_emails,
                        bcc_emails=bcc_emails,
                        subject=subject_supplier,
                        html_content=html_content_supplier,
                        reply_to="dispatch@trydownstream.com",
                    )
        except Exception as e:
            logger.error(
                f"Order.send_supplier_approval_email: [{self.id}]-[{e}]", exc_info=e
            )

    def close_admin_chat(self, message=None):
        if self.intercom_id:
            try:
                IntercomConversation.close(self.intercom_id)
            except Exception as e:
                logger.error(f"close_admin_chat: [{self.id}]-[{e}]", exc_info=e)

    def create_admin_chat(self, conversation_id: str):
        """
        Create an Intercom Conversation for the Order between the Seller and the Admin.
        """
        if self.intercom_id and self.intercom_id != conversation_id:
            try:
                logger.warning(
                    f"create_admin_chat:close previous chat: old chat:[{self.intercom_id}]-new:[{conversation_id}]"
                )
                # Close the previous chat
                IntercomConversation.close(self.intercom_id)
            except Exception as e:
                logger.error(
                    f"create_admin_chat:close previous chat: [{self.id}]-[{e}]",
                    exc_info=e,
                )
        try:
            self.intercom_id = conversation_id
            self.save()
            # Attach the all parties, with access to this location, to the conversation
            user_seller_locations = (
                get_user_seller_location_model()
                .objects.filter(
                    seller_location_id=self.order_group.seller_product_seller_location.seller_location_id
                )
                .select_related("user")
            )
            seller_user = (
                get_our_user_model()
                .objects.filter(
                    user_group__seller=self.order_group.seller_product_seller_location.seller_location.seller
                )
                .filter(type=UserType.ADMIN)
                .first()
            )
            attach_users = []
            if not user_seller_locations.exists() and seller_user is not None:
                attach_users.append(seller_user.intercom_id)
            for user_seller_location in user_seller_locations:
                attach_users.append(user_seller_location.user.intercom_id)
            if attach_users:
                IntercomConversation.attach_users_conversation(
                    attach_users, self.intercom_id
                )
                # Detach the Downstream Sender user from the conversation so that converation is between admin and seller.
                IntercomConversation.detach_users_conversation(
                    ["65f84e6bfc65b05f40b1e556"], self.intercom_id
                )
            else:
                logger.error(
                    f"create_admin_chat:attach_users: no users found for seller_location_id:[{self.order_group.seller_product_seller_location.seller_location_id}]"
                )

            # Add Booking tag to conversation
            IntercomConversation.attach_booking_tag(conversation_id)
        except Exception as e:
            logger.error(f"create_admin_chat:reply [{self.id}]-[{e}]", exc_info=e)

    def create_customer_chat(self, user_intercom_id: str):
        """
        Create an Intercom Conversation for the Order between the Seller and the Customer.
        """
        if self.order_type is None:
            subject = f"Downstream Booking: { self.order_group.seller_product_seller_location.seller_product.product.main_product.name } at {self.order_group.user_address.formatted_address()} | reference ID: {self.id}."
        else:
            subject = f"Downstream Booking: {self.order_type} on { self.order_group.seller_product_seller_location.seller_product.product.main_product.name } at {self.order_group.user_address.formatted_address()} | reference ID: {self.id}."
        if self.custmer_intercom_id:
            try:
                body = subject
                if settings.ENVIRONMENT != "TEST":
                    body = f"{body} - Michael Wickey Intercom Test"
                # TODO: Only send the message if this is a new Order and is not yet in the chat
                # html_content_supplier = render_to_string(
                #     "supplier_dashboard/new_order_chat.html",
                #     {"order": order},
                # )
                # IntercomConversation.admin_reply(
                #     self.custmer_intercom_id, user_intercom_id, html_content_supplier
                # )
            except Exception as e:
                logger.error(
                    f"create_customer_chat:reply [{self.id}]-[{e}]", exc_info=e
                )
        else:
            try:
                body = f"{subject} This is a chat between Seller and Client."
                if settings.ENVIRONMENT != "TEST":
                    body = f"{body} - Michael Wickey Intercom Test"
                html_content_supplier = render_to_string(
                    "supplier_dashboard/new_order_chat.html",
                    {"order": self},
                )
                message_data = IntercomConversation.send_message(
                    user_intercom_id, subject, html_content_supplier
                )
                conversation_id = message_data["conversation_id"]
                self.custmer_intercom_id = conversation_id
                self.save()
                # Attach the all parties, with access to this location, to the conversation
                # TODO: Attach customers from UserUserAddresses
                user_seller_locations = (
                    get_user_seller_location_model()
                    .objects.filter(
                        seller_location_id=self.order_group.seller_product_seller_location.seller_location_id
                    )
                    .select_related("user")
                )
                attach_users = [user_intercom_id, self.order_group.user.intercom_id]
                for user_seller_location in user_seller_locations:
                    attach_users.append(user_seller_location.user.intercom_id)
                IntercomConversation.attach_users_conversation(
                    attach_users, self.custmer_intercom_id
                )
                # Add Booking tag to conversation
                IntercomConversation.attach_booking_tag(conversation_id)
            except Exception as e:
                logger.error(
                    f"create_customer_chat:reply [{self.id}]-[{e}]", exc_info=e
                )

    def get_price(self):
        """Get the Order with tax details.
        This is also used as the Quote in the Admin Portal.
        Returns PricingEngineResponseSerializer."""

        try:
            # Load all line items
            pricing = {}
            all_line_items = []
            delivery_fee = 0
            re_get_taxes = False
            for order_line_item in self.order_line_items.all():
                if order_line_item.stripe_invoice_line_item_id != "BYPASS":
                    if (
                        order_line_item.tax is None
                        and order_line_item.customer_price() > 0
                    ):
                        re_get_taxes = True
                all_line_items.append(order_line_item)
                if order_line_item.order_line_item_type.code == "DELIVERY":
                    delivery_fee = float(order_line_item.customer_price())

            # Calculate the tax details
            if (
                self.order_group.user_address.user_group
                and self.order_group.user_address.user_group.tax_exempt_status
                == "exempt"
            ):
                tax_details = {"rate": float(0.00), "taxes": float(0.00)}
            else:
                # Only get taxes if re_get_taxes is True.
                if re_get_taxes:
                    # Get taxes and also update the line items with the tax amount.
                    tax_details = StripeUtils.PriceCalculation.calculate_price_details(
                        self, all_line_items, delivery_fee, update_line_items=True
                    )

            # Load all line items into a PricingEngine response
            for order_line_item in all_line_items:
                customer_rate = float(
                    order_line_item.rate
                    * (1 + (order_line_item.platform_fee_percent / 100))
                )
                _dd = get_pricing_line_item_model()(
                    description=order_line_item.description,
                    unit_price=customer_rate,
                    quantity=order_line_item.quantity,
                    units=order_line_item.order_line_item_type.units,
                    tax=order_line_item.tax,
                )
                key = order_line_item.order_line_item_type.code
                try:
                    pricing[key][1].append(_dd)
                except KeyError:
                    pricing[key] = (
                        get_pricing_line_item_group_model()(
                            title=order_line_item.order_line_item_type.name,
                            code=order_line_item.order_line_item_type.code.lower(),
                        ),
                        [_dd],
                    )
            pricing_list = [item for item in pricing.values()]
            return get_pricing_engine_response_serializer()(pricing_list).data
        except Exception as e:
            logger.error(f"Order.get_price: [{self.id}]-[{e}]", exc_info=e)
            return None

    def submit_order(self, override_approval_policy=False):
        """This method is used to submit an Order (set status to PENDING and set submitted_on to now).
        It will check if the Order needs approval before it can be submitted.
        If the Order needs approval and override_approval_policy is False, then it will raise a ValidationError.
        If the Order needs approval and override_approval_policy is True, then it will approve the Order and submit it.
        """
        if not self.submitted_on:
            # Check if order needed approval
            if self.status == Order.Status.ADMIN_APPROVAL_PENDING:
                if not override_approval_policy:
                    raise ValidationError(
                        "Order needs approval before it can be submitted."
                    )
                order_approval = (
                    get_order_approval_model().objects.filter(order_id=self.id).first()
                )
                if order_approval:
                    # Order Approval has a pre_save signal to submit the order.
                    order_approval.status = ApprovalStatus.APPROVED
                    order_approval.save()
                else:
                    # For some reason, the order_approval is missing. This should not happen.
                    # But if it does, then just submit the order.
                    self.status = Order.Status.PENDING
                    self.submitted_on = timezone.now()
                    self.save()
            else:
                if self.status == Order.Status.CREDIT_APPLICATION_APPROVAL_PENDING:
                    raise ValidationError(
                        "Order is pending a credit application approval and cannot be submitted."
                    )
                if self.status == Order.Status.CREDIT_APPLICATION_DECLINED:
                    raise ValidationError(
                        "Order has been denied a credit application approval and cannot be submitted."
                    )
                if self.status == Order.Status.NO_PAYMENT_METHOD:
                    raise ValidationError(
                        "Order has no payment methods on file and cannot be submitted."
                    )
                if self.status == Order.Status.ADMIN_APPROVAL_DECLINED:
                    raise ValidationError(
                        "Order has been declined by Admin and cannot be submitted."
                    )
                if self.status == Order.Status.CANCELLED:
                    raise ValidationError(
                        "Order has been cancelled and cannot be submitted."
                    )
                if self.status == Order.Status.COMPLETE:
                    raise ValidationError(
                        "Order has been completed and cannot be submitted."
                    )
                self.status = Order.Status.PENDING
                self.submitted_on = timezone.now()
                self.save()

    def __str__(self):
        return (
            self.order_group.seller_product_seller_location.seller_product.product.main_product.name
            + " - "
            + self.order_group.user_address.name
        )


post_save.connect(Order.post_save, sender=Order)
