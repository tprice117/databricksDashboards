import datetime
import logging

import mailchimp_transactional as MailchimpTransactional
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.template.loader import render_to_string

from api.models.disposal_location.disposal_location import DisposalLocation
from api.models.order.order_line_item import OrderLineItem
from api.models.order.order_line_item_type import OrderLineItemType
from api.models.track_data import track_data
from api.utils.auth0 import get_password_change_url, get_user_data
from common.models import BaseModel
from notifications.utils.add_email_to_queue import add_email_to_queue
from api.utils.utils import encrypt_string

logger = logging.getLogger(__name__)

mailchimp = MailchimpTransactional.Client(settings.MAILCHIMP_API_KEY)


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

    PENDING = "PENDING"
    SCHEDULED = "SCHEDULED"
    INPROGRESS = "IN-PROGRESS"
    AWAITINGREQUEST = "Awaiting Request"
    CANCELLED = "CANCELLED"
    COMPLETE = "COMPLETE"

    STATUS_CHOICES = (
        (PENDING, "Pending"),
        (SCHEDULED, "Scheduled"),
        (INPROGRESS, "In-Progress"),
        (AWAITINGREQUEST, "Awaiting Request"),
        (CANCELLED, "Cancelled"),
        (COMPLETE, "Complete"),
    )

    order_group = models.ForeignKey(
        "api.OrderGroup", models.PROTECT, related_name="orders"
    )
    disposal_location = models.ForeignKey(
        DisposalLocation, models.DO_NOTHING, blank=True, null=True
    )
    start_date = models.DateField()
    end_date = models.DateField()
    submitted_on = models.DateTimeField(blank=True, null=True)
    schedule_details = models.TextField(
        blank=True, null=True
    )  # 6.6.23 (Modified name to schedule_details from additional_schedule_details)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    billing_comments_internal_use = models.TextField(blank=True, null=True)  # 6.6.23
    schedule_window = models.CharField(
        max_length=35,
        choices=[
            ("Morning (7am-11am)", "Morning (7am-11am)"),
            ("Afternoon (12pm-4pm)", "Afternoon (12pm-4pm)"),
            ("Evening (5pm-8pm)", "Evening (5pm-8pm)"),
        ],
        blank=True,
        null=True,
    )  # 6.6.23
    __original_submitted_on = None

    def __init__(self, *args, **kwargs):
        super(Order, self).__init__(*args, **kwargs)
        self.__original_submitted_on = self.submitted_on
        self.__original_status = self.status

    @property
    def order_type(self):
        return self.get_order_type()

    def customer_price(self):
        return sum(
            [
                order_line_item.rate
                * order_line_item.quantity
                * (1 + (order_line_item.platform_fee_percent / 100))
                for order_line_item in self.order_line_items.all()
            ]
        )

    def seller_price(self):
        seller_price = sum(
            [
                order_line_item.rate * order_line_item.quantity
                for order_line_item in self.order_line_items.all()
            ]
        )
        return round(seller_price, 2)

    def total_paid_to_seller(self):
        total_paid_to_seller = sum([payout.amount for payout in self.payouts.all()])
        return round(total_paid_to_seller, 2)

    def needed_payout_to_seller(self):
        return round(self.seller_price() - self.total_paid_to_seller(), 2)

    def stripe_invoice_summary_item_description(self):
        return f'{self.order_group.seller_product_seller_location.seller_product.product.main_product.name} | {self.start_date.strftime("%a, %b %-d")} - {self.end_date.strftime("%a, %b %-d")} | {str(self.id)[:5]}'

    def get_order_type(self):
        # Assign variables comparing Order StartDate and EndDate to OrderGroup StartDate and EndDate.
        order_order_group_start_date_equal = (
            self.start_date == self.order_group.start_date
        )
        order_order_group_end_dates_equal = self.end_date == self.order_group.end_date

        # Does the OrderGroup have a Subscription?
        has_subscription = hasattr(self.order_group, "subscription")

        # Are Order.StartDate and Order.EndDate equal?
        order_start_end_dates_equal = self.start_date == self.end_date

        # Assign variables based on Order.Type.
        # DELIVERY: Order.StartDate == OrderGroup.StartDate AND Order.StartDate == Order.EndDate
        # AND Order.EndDate != OrderGroup.EndDate.
        order_type_delivery = (
            order_order_group_start_date_equal
            and order_start_end_dates_equal
            and not order_order_group_end_dates_equal
        )
        # Return directly is true so that total order lookup doesn't happen.
        if order_type_delivery:
            return Order.Type.DELIVERY

        # Orders in OrderGroup.
        order_count = Order.objects.filter(order_group=self.order_group).count()

        # ONE TIME: Order.StartDate == OrderGroup.StartDate AND Order.EndDate == OrderGroup.EndDate
        # AND OrderGroup has no Subscription.
        order_type_one_time = (
            order_count == 1
            and order_order_group_start_date_equal
            and order_order_group_end_dates_equal
            and not has_subscription
        )
        # REMOVAL: Order.EndDate == OrderGroup.EndDate AND OrderGroup.Orders.Count > 1.
        order_type_removal = order_order_group_end_dates_equal and order_count > 1
        # SWAP: OrderGroup.Orders.Count > 1 AND Order.EndDate != OrderGroup.EndDate AND OrderGroup has no Subscription.
        order_type_swap = (
            order_count > 1
            and not order_order_group_end_dates_equal
            and not has_subscription
        )
        # AUTO RENEWAL: OrderGroup has Subscription and does not meet any other criteria.
        order_type_auto_renewal = (
            has_subscription
            and not order_type_delivery
            and not order_type_one_time
            and not order_type_removal
            and not order_type_swap
        )

        if order_type_delivery:
            return Order.Type.DELIVERY
        elif order_type_one_time:
            return Order.Type.ONE_TIME
        elif order_type_removal:
            return Order.Type.REMOVAL
        elif order_type_swap:
            return Order.Type.SWAP
        elif order_type_auto_renewal:
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

    def clean(self):
        super().clean()

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
            Order.objects.filter(
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
        # Only 1 Order from an OrderGroup can be in the cart
        # (Order.submittedDate == null) at a time.
        elif (
            Order.objects.filter(
                order_group=self.order_group,
                submitted_on__isnull=True,
            )
            .exclude(id=self.id)
            .count()
            > 1
        ):
            raise ValidationError(
                "Only 1 Order from an OrderGroup can be in the cart at a time"
            )

    def post_save(sender, instance, created, **kwargs):
        order_line_items = OrderLineItem.objects.filter(order=instance)
        # if instance.submitted_on_has_changed and order_line_items.count() == 0:
        if created and order_line_items.count() == 0:
            try:
                # Create Delivery Fee OrderLineItem.
                order_group_orders = Order.objects.filter(
                    order_group=instance.order_group
                )
                if order_group_orders.count() == 0:
                    delivery_fee = 0
                    if instance.order_group.seller_product_seller_location.delivery_fee:
                        delivery_fee = (
                            instance.order_group.seller_product_seller_location.delivery_fee
                        )
                    OrderLineItem.objects.create(
                        order=instance,
                        order_line_item_type=OrderLineItemType.objects.get(
                            code="DELIVERY"
                        ),
                        rate=delivery_fee,
                        quantity=1,
                        description="Delivery Fee",
                        platform_fee_percent=instance.order_group.take_rate,
                        is_flat_rate=True,
                    )

                # Create Removal Fee OrderLineItem.
                if (
                    instance.order_group.end_date == instance.end_date
                    and order_group_orders.count() > 1
                ):
                    removal_fee = 0
                    if instance.order_group.seller_product_seller_location.removal_fee:
                        removal_fee = (
                            instance.order_group.seller_product_seller_location.removal_fee
                        )
                    OrderLineItem.objects.create(
                        order=instance,
                        order_line_item_type=OrderLineItemType.objects.get(
                            code="REMOVAL"
                        ),
                        rate=removal_fee,
                        quantity=1,
                        description="Removal Fee",
                        platform_fee_percent=instance.order_group.take_rate,
                        is_flat_rate=True,
                    )
                    # Don't add any other OrderLineItems if this is a removal.
                    return

                # Create OrderLineItems for newly "submitted" order.
                # Service Price.
                if hasattr(instance.order_group, "service"):
                    order_line_item_type = OrderLineItemType.objects.get(code="SERVICE")
                    OrderLineItem.objects.create(
                        order=instance,
                        order_line_item_type=order_line_item_type,
                        rate=instance.order_group.service.rate,
                        quantity=instance.order_group.service.miles or 1,
                        is_flat_rate=instance.order_group.service.miles is None,
                        platform_fee_percent=instance.order_group.take_rate,
                    )

                # Rental Price.
                if hasattr(instance.order_group, "rental"):
                    day_count = (
                        (instance.end_date - instance.start_date).days
                        if instance.end_date
                        else 0
                    )
                    days_over_included = (
                        day_count - instance.order_group.rental.included_days
                    )
                    order_line_item_type = OrderLineItemType.objects.get(code="RENTAL")

                    # Create OrderLineItem for Included Days.
                    OrderLineItem.objects.create(
                        order=instance,
                        order_line_item_type=order_line_item_type,
                        rate=instance.order_group.rental.price_per_day_included,
                        quantity=instance.order_group.rental.included_days,
                        description="Included Days",
                        platform_fee_percent=instance.order_group.take_rate,
                    )

                    # Create OrderLineItem for Additional Days.
                    if days_over_included > 0:
                        OrderLineItem.objects.create(
                            order=instance,
                            order_line_item_type=order_line_item_type,
                            rate=instance.order_group.rental.price_per_day_additional,
                            quantity=days_over_included,
                            description="Additional Days",
                            platform_fee_percent=instance.order_group.take_rate,
                        )

                # Material Price.
                if hasattr(instance.order_group, "material"):
                    tons_over_included = (
                        instance.order_group.tonnage_quantity or 0
                    ) - instance.order_group.material.tonnage_included
                    order_line_item_type = OrderLineItemType.objects.get(
                        code="MATERIAL"
                    )

                    # Create OrderLineItem for Included Tons.
                    OrderLineItem.objects.create(
                        order=instance,
                        order_line_item_type=order_line_item_type,
                        rate=instance.order_group.material.price_per_ton,
                        quantity=instance.order_group.material.tonnage_included,
                        description="Included Tons",
                        platform_fee_percent=instance.order_group.take_rate,
                    )

                    # Create OrderLineItem for Additional Tons.
                    if tons_over_included > 0:
                        OrderLineItem.objects.create(
                            order=instance,
                            order_line_item_type=order_line_item_type,
                            rate=instance.order_group.material.price_per_ton,
                            quantity=tons_over_included,
                            description="Additional Tons",
                            platform_fee_percent=instance.order_group.take_rate,
                        )
            except Exception as e:
                logger.error(f"Order.post_save: [{e}]", exc_info=e)

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
                        f"Order.send_customer_email_when_order_scheduled: [Use default: {call_to_action_url}]-[{e}]",
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
                    f"Order.send_customer_email_when_order_scheduled: [{e}]", exc_info=e
                )

    def send_supplier_approval_email(self):
        # Send email to supplier. Only CC on our PROD environment.
        bcc_emails = []
        if settings.ENVIRONMENT == "TEST":
            bcc_emails.append("dispatch@trydownstream.com")

        try:
            if self.order_type != Order.Type.AUTO_RENEWAL:
                # The accept button redirects to our server, which will decrypt order_id to ensure it origniated from us,
                # then it opens the order html to allow them to select order status.
                base_url = settings.API_URL
                accept_url = f"{base_url}/api/order/{self.id}/view/?key={encrypt_string(str(self.id))}"
                subject_supplier = f"🚀 Yippee! New {self.order_type} Downstream Booking Landed! [{str(self.id)}]"
                html_content_supplier = render_to_string(
                    "notifications/emails/supplier_email.min.html",
                    {"order": self, "accept_url": accept_url, "is_email": True},
                )
                add_email_to_queue(
                    from_email="dispatch@trydownstream.com",
                    to_emails=[
                        self.order_group.seller_product_seller_location.seller_location.order_email
                    ],
                    bcc_emails=bcc_emails,
                    subject=subject_supplier,
                    html_content=html_content_supplier,
                    reply_to="dispatch@trydownstream.com",
                )
        except Exception as e:
            logger.error(f"Order.send_supplier_approval_email: [{e}]", exc_info=e)

    def __str__(self):
        return (
            self.order_group.seller_product_seller_location.seller_product.product.main_product.name
            + " - "
            + self.order_group.user_address.name
        )


post_save.connect(Order.post_save, sender=Order)


@receiver(pre_save, sender=Order)
def pre_save_order(sender, instance: Order, **kwargs):
    #  Check if Order is being created.
    creating = not Order.objects.filter(id=instance.id).exists()

    if creating:
        # Get all Orders for this UserGroup this month.
        orders_this_month = Order.objects.filter(
            submitted_on__gte=datetime.datetime.now().replace(day=1),
        )

        # Calculate the total of all Orders for this UserGroup this month.
        order_total_this_month = sum(
            [order.customer_price() for order in orders_this_month]
        )

        # Check that UserGroupPolicyMonthlyLimit will not be exceeded with
        # this Order.
        if instance.order_group.user_address.user_group.policy_monthly_limit and (
            order_total_this_month + instance.customer_price()
            > instance.order_group.user_address.user_group.policy_monthly_limit
        ):
            raise ValidationError(
                "Monthly Order Limit has been exceeded. This Order will be sent to your Admin for approval."
            )
        # Check that UserGroupPolicyPurchaseApproval will not be exceeded with
        # this Order.
        elif hasattr(
            instance.order_group.user_address.user_group, "policy_purchase_approval"
        ) and (
            instance.customer_price()
            > instance.order_group.user_address.user_group.policy_purchase_approval
        ):
            raise ValidationError(
                "Purchase Approval Limit has been exceeded. This Order will be sent to your Admin for approval."
            )
