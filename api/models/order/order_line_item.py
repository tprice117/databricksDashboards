from django.db import models
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from api.models.order.order_items.order_insurance import OrderInsurance
from api.models.order.order_line_item_type import OrderLineItemType
from api.models.track_data import track_data
from common.models import BaseModel
from common.utils.stripe.stripe_utils import StripeUtils

TIME_UNITS = [
    "day",
    "days",
    "week",
    "weeks",
    "month",
    "months",
    "year",
    "years",
]

EXPECTED_ONE_STEP_TYPES = [
    "RENTAL",
    "SERVICE",
    "FUEL_AND_ENV",
    "DELIVERY",
    "REMOVAL",
]

EXPECTED_TWO_STEP_TYPES = [
    "RENTAL",
    "SERVICE",
    "MATERIAL",
    "FUEL_AND_ENV",
    "DELIVERY",
    "REMOVAL",
]

EXPECTED_MULTI_STEP_TYPES = [
    "RENTAL",
    "FUEL_AND_ENV",
    "DELIVERY",
    "REMOVAL",
]

# Define the item order: RPP, PERMIT, DAMAGE
ITEM_ORDER = [
    "SERVICE",
    "RENTAL",
    "RELOCATION",
    "MATERIAL",
    "FUEL_AND_ENV",
    "DELIVERY",
    "REMOVAL",
]


class OrderLineItemManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset()

    def exclude_adjustments(self):
        return self.get_queryset().exclude(stripe_invoice_line_item_id="BYPASS")

    def ordered_by_type(self):
        # Create a case statement to order by the specified item order
        order_case = models.Case(
            *[
                models.When(order_line_item_type__code=item, then=pos)
                for pos, item in enumerate(ITEM_ORDER)
            ]
        )
        return (
            self.exclude_adjustments()
            .annotate(order_case=order_case)
            .order_by("order_case")
        )


@track_data("rate", "quantity", "tax", "platform_fee_percent")
class OrderLineItem(BaseModel):
    class PaymentStatus(models.TextChoices):
        NOT_INVOICED = "not_invoiced"
        INVOICED = "invoiced"
        PAID = "paid"

    order = models.ForeignKey(
        "api.Order",
        models.CASCADE,
        related_name="order_line_items",
    )
    order_line_item_type = models.ForeignKey(
        OrderLineItemType,
        models.PROTECT,
    )
    rate = models.DecimalField(
        max_digits=18,
        decimal_places=2,
    )
    quantity = models.DecimalField(
        max_digits=18,
        decimal_places=4,
    )
    platform_fee_percent = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=20,
        help_text="Enter as a percentage without the percent symbol (ex: 25.00)",
    )
    tax = models.DecimalField(
        max_digits=18,
        decimal_places=4,
        blank=True,
        null=True,
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )
    is_flat_rate = models.BooleanField(default=False)
    stripe_invoice_line_item_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )
    paid = models.BooleanField(
        default=False,
    )
    backbill = models.BooleanField(
        default=False,
    )

    objects = OrderLineItemManager()  # Use the custom manager

    def __str__(self):
        return str(self.order) + " - " + self.order_line_item_type.name

    class Meta:
        verbose_name = "Transaction Line Item"
        verbose_name_plural = "Transaction Line Items"

    def get_units(self):
        if (
            self.order.order_group.seller_product_seller_location.seller_product.product.main_product.has_rental_one_step
            and (
                self.order_line_item_type.code == "RENTAL"
                or self.order_line_item_type.code == "SERVICE"
            )
        ):
            return "month"
        elif (
            self.order.order_group.seller_product_seller_location.seller_product.product.main_product.has_rental_multi_step
            and self.description
            and (
                self.order_line_item_type.code == "RENTAL"
                or self.order_line_item_type.code == "SERVICE"
            )
        ):
            return self.description
        else:
            return self.order_line_item_type.units

    @property
    def stripe_description(self):
        has_rental_one_step = (
            self.order.order_group.seller_product_seller_location.seller_product.product.main_product.has_rental_one_step
        )
        has_rental_multi_step = (
            self.order.order_group.seller_product_seller_location.seller_product.product.main_product.has_rental_multi_step
        )
        has_service_times_per_week = (
            self.order.order_group.seller_product_seller_location.seller_product.product.main_product.has_service_times_per_week
        )
        unit_str = (
            self.order_line_item_type.units
            if self.order_line_item_type.units
            else "unit"
        )
        if unit_str == "Dollars":
            unit_str = ""
        if unit_str is None:
            unit_str = ""

        # Handle expected line item types for each rental type.
        # All other line item types will be handled by the default case, which is same as the below.
        # Order Type | # Qty @ Rate (description) = total
        customer_price = self.customer_price()
        rate = customer_price / self.quantity if self.quantity > 0 else 0
        total = customer_price
        # Check if self.quantity is a whole number.
        if self.quantity % 1 == 0:
            quantity = int(self.quantity)
        else:
            quantity = self.quantity

        if self.order_line_item_type.code == "FUEL_AND_ENV":
            # e.g. Fuel & Fees (15.00%) = $25.51
            order_line_items = self.order.order_line_items.exclude(
                stripe_invoice_line_item_id="BYPASS"
            ).exclude(order_line_item_type__code="FUEL_AND_ENV")
            subtotal = 0
            markup = 0
            for order_line_item in order_line_items:
                subtotal += order_line_item.customer_price()

            if subtotal:
                # calculate the fuel and environmental fee percentage
                markup = customer_price / subtotal

            if markup:
                unit_str = f"{markup * 100:.3f}%"
            # if self.order.order_group.seller_product_seller_location.fuel_environmental_markup:
            #     unit_str = f"{self.order.order_group.seller_product_seller_location.fuel_environmental_markup}%"
            else:
                unit_str = "0%"

            if total > 0 and unit_str == "0%":
                description = f"Fuel & Fees | ${total:,.2f} = ${total:,.2f}"
            else:
                description = (
                    f"Fuel & Fees | ${subtotal:,.2f} @ {unit_str} = ${total:,.2f}"
                )
            return description

        if (
            self.order_line_item_type.code == "DELIVERY"
            or self.order_line_item_type.code == "REMOVAL"
        ):
            # e.g. Delivery | # 1 @ $135 = $135
            description = (
                f"{self.order_line_item_type.name} | # {quantity} @ ${rate:,.2f}"
            )
            if self.description:
                updated_description = self.description.replace(
                    self.order_line_item_type.name, ""
                )
                if updated_description:
                    description += f" ({updated_description})"
            description += f" = ${total:,.2f}"
            return description

        if has_rental_one_step:
            if self.order_line_item_type.code in EXPECTED_ONE_STEP_TYPES:
                # e.g. Service $135.00/month (One Time Per Week) = $135
                # Rental $54.25/month = $54.25
                if (
                    self.order_line_item_type.code == "RENTAL"
                    or self.order_line_item_type.code == "SERVICE"
                ):
                    unit_str = "month"
                subdescription = ""
                if self.description:
                    subdescription = f" ({self.description})"
                if (
                    self.order_line_item_type.code == "SERVICE"
                    and has_service_times_per_week
                    and self.order.order_group.times_per_week
                    and self.order.order_group.service_times_per_week
                ):
                    if self.description:
                        # Check if description contains the word time and week case insensitive
                        # TODO: Change this back to the original code once the system can handle once every two weeks
                        if (
                            "time" in self.description.lower()
                            and "week" in self.description.lower()
                        ):
                            subdescription = f" ({self.description})"
                        else:
                            subdescription = f" ({self.order.order_group.times_per_week} service per week)"
                    # subdescription = (
                    #     f" ({self.order.order_group.times_per_week} service per week)"
                    # )

                slash_description = ""
                if unit_str:
                    slash_description = f"/{unit_str}{subdescription}"
                else:
                    slash_description = f" @ {quantity}"
                description = (
                    self.order_line_item_type.name
                    + f" | ${rate:,.2f}"
                    + slash_description
                    + f" = ${total:,.2f}"
                )
                return description
        elif has_rental_multi_step:
            if self.order_line_item_type.code in EXPECTED_MULTI_STEP_TYPES:
                # e.g. Rental $50.00/day @ 3 days = $150
                # Rental $200.00/day @ 1 week = $200
                subdescription = ""
                if (
                    self.order_line_item_type.code == "RENTAL"
                    or self.order_line_item_type.code == "SERVICE"
                ) and self.description:
                    unit_str = self.description

                slash_description = ""
                unit_str = unit_str.lower()
                unit_str_single = unit_str
                if self.order_line_item_type.code == "RENTAL":
                    # if not day, week, month, year, etc, then just show the unit
                    if unit_str in TIME_UNITS:
                        if unit_str.endswith("s"):
                            unit_str_single = unit_str[:-1]
                        if quantity <= 1:
                            unit_str = unit_str_single

                    slash_description = (
                        f"/{unit_str_single}{subdescription} @ {quantity} {unit_str}"
                    )
                else:
                    if unit_str:
                        slash_description = f" @ {quantity} {unit_str}"
                    else:
                        slash_description = f" @ {quantity}"
                description = (
                    self.order_line_item_type.name
                    + f" | ${rate:,.2f}"
                    + slash_description
                    + f" = ${total:,.2f}"
                )
                return description
        else:
            if self.order_line_item_type.code in EXPECTED_TWO_STEP_TYPES:
                subdescription = ""
                if self.description:
                    subdescription = f" ({self.description})"

                slash_description = ""
                if self.order_line_item_type.code == "SERVICE":
                    slash_description = f" @{subdescription}"
                elif (
                    self.order_line_item_type.code == "RENTAL"
                    or self.order_line_item_type.code == "MATERIAL"
                ):
                    unit_str = unit_str.lower()
                    unit_str_single = unit_str
                    if unit_str and unit_str.endswith("s"):
                        unit_str_single = unit_str[:-1]
                    if quantity <= 1:
                        unit_str = unit_str_single

                    slash_description = (
                        f"/{unit_str_single} @ {quantity} {unit_str}{subdescription}"
                    )
                else:
                    if unit_str:
                        slash_description = f" @ {quantity} {unit_str}"
                    else:
                        slash_description = f" @ {quantity}"
                description = (
                    self.order_line_item_type.name
                    + f" | ${rate:,.2f}"
                    + slash_description
                    + f" = ${total:,.2f}"
                )
                return description

        description = f"{self.order_line_item_type.name} | # {quantity} @ ${rate:,.2f}"
        if self.description:
            description += f" ({self.description})"
        description += f" = ${total:,.2f}"

        return description

    def get_invoice(self):
        if self.stripe_invoice_line_item_id:
            try:
                invoice_line_item = StripeUtils.InvoiceItem.get(
                    self.stripe_invoice_line_item_id
                )
                return StripeUtils.Invoice.get(invoice_line_item.invoice)
            except:
                # Return None if Stripe Invoice or Stripe Invoice Line Item does not exist.
                return None
        else:
            return None

    def payment_status(self):
        if not self.stripe_invoice_line_item_id:
            # Return None if OrderLineItem is not associated with an Invoice.
            return self.PaymentStatus.NOT_INVOICED
        elif self.stripe_invoice_line_item_id == "BYPASS":
            # Return True if OrderLineItem.StripeInvoiceLineItemId == "BYPASS".
            # BYPASS is used for OrderLineItems that are not associated with a
            # Stripe Invoice, but have been paid for by the customer.
            return self.PaymentStatus.PAID
        elif self.paid:
            # Return True if OrderLineItem.Paid == True. See below for how
            # OrderLineItem.Paid is set.
            return self.PaymentStatus.PAID
        else:
            # If OrderLineItem.StripeInvoiceLineItemId is populated and is not
            # "BYPASS" or OrderLineItem.Paid == False, the Order Line Item is
            # invoiced, but not paid.
            return self.PaymentStatus.INVOICED

    def seller_payout_price(self):
        return round((self.rate or 0) * (self.quantity or 0), 2)

    def customer_price(self):
        seller_price = self.seller_payout_price()
        customer_price = seller_price * (1 + (self.platform_fee_percent / 100))
        return round(customer_price, 2)

    def customer_price_with_tax(self):
        seller_price = self.seller_payout_price()
        customer_price = seller_price * (1 + (self.platform_fee_percent / 100))
        if self.tax:
            customer_price += self.tax
        return round(customer_price, 2)


@receiver(pre_save, sender=OrderLineItem)
def order_line_item_pre_save(sender, instance, **kwargs):
    if (
        instance.has_changed("rate")
        or instance.has_changed("quantity")
        or instance.has_changed("platform_fee_percent")
    ):
        # Invalidate tax: It will be updated the next time this order is retrieved to be viewed via the API or Quoted
        instance.taxes = None


# Signal to handle post_save event for new instances with PENDING status
@receiver(post_save, sender=OrderLineItem)
def order_line_item_post_save(
    sender,
    instance: OrderLineItem,
    created,
    **kwargs,
):
    # On every save, call the update_order_insurance method to adjust the
    # OrderInsurance items, if necessary.
    OrderInsurance.update_order_insurance()
