import logging
from typing import List

import stripe
from django.conf import settings
from django.contrib import admin, messages
from django.utils.html import format_html

from api.admin.filters import CreatedDateFilter
from api.admin.filters.order.admin_tasks import OrderAdminTasksFilter
from api.admin.inlines import (
    OrderDisposalTicketInline,
    OrderLineItemInline,
    PayoutInline,
    SellerInvoicePayableLineItemInline,
)
from api.models import (
    Order,
    OrderLineItem,
    Payout,
    SellerInvoicePayableLineItem,
    SellerLocation,
    UserAddress,
)
from api.utils.lob import Lob, CheckErrorResponse

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    model = Order
    readonly_fields = ("auto_order_type", "customer_price", "seller_price")
    search_fields = ("id",)
    list_display = (
        "order_group",
        "start_date",
        "end_date",
        "auto_order_type",
        "status",
        "customer_price",
        "customer_invoiced",
        "customer_paid",
        "payment_status",
        "seller_price",
        "total_paid_to_seller",
        "payout_status",
        "total_invoiced_from_seller",
        "seller_invoice_status",
    )
    list_filter = (
        "status",
        CreatedDateFilter,
        OrderAdminTasksFilter,
    )
    inlines = [
        OrderLineItemInline,
        OrderDisposalTicketInline,
        PayoutInline,
        SellerInvoicePayableLineItemInline,
    ]
    actions = [
        "send_payouts",
        "send_supplier_approval_email",
    ]

    def auto_order_type(self, obj: Order):
        return obj.get_order_type()

    @admin.action(description="Send payouts")
    def send_payouts(self, request, queryset):
        # Get distinct SellerLocations.
        distinct_seller_locations: List[SellerLocation] = []
        for order in queryset:
            seller_location = (
                order.order_group.seller_product_seller_location.seller_location
            )
            current_seller_location_ids = [
                seller_location.id for seller_location in distinct_seller_locations
            ]
            if seller_location.id not in current_seller_location_ids:
                distinct_seller_locations.append(seller_location)

        # For each SellerLocation, send payouts for all orders.
        for seller_location in distinct_seller_locations:
            orders_for_seller_location = queryset.filter(
                order_group__seller_product_seller_location__seller_location=seller_location
            )

            if seller_location.stripe_connect_account_id:
                print("Payout via Stripe")
                # If connected with Stripe Connnect, payout via Stripe.
                for order in orders_for_seller_location:
                    # Only send payout if seller has a Stripe Connect Account.
                    payout_diff = self.seller_price(order) - self.total_paid_to_seller(
                        order
                    )
                    if payout_diff > 0:
                        try:
                            # Payout via Stripe.
                            transfer = stripe.Transfer.create(
                                amount=round(payout_diff * 100),
                                currency="usd",
                                destination=order.order_group.seller_product_seller_location.seller_location.stripe_connect_account_id,
                            )

                            # Save Payout.
                            Payout.objects.create(
                                order=order,
                                amount=payout_diff,
                                stripe_transfer_id=transfer.id,
                            )
                        except Exception as ex:
                            print("Error: " + str(ex))
                            logger.error(
                                f"OrderAdmin.send_payouts: [{ex}]", exc_info=ex
                            )
            elif seller_location.payee_name and hasattr(
                seller_location, "mailing_address"
            ):
                print("Payout via Checkbook")
                # If not connected with Stripe Connect, but [payee_name] and
                # [mailing_address] are set, payout via Checkbook.
                amount_to_send = 0

                # Compute total amount to be sent.
                for order in orders_for_seller_location:
                    payout_diff = self.seller_price(order) - self.total_paid_to_seller(
                        order
                    )
                    if payout_diff > 0:
                        amount_to_send += payout_diff

                # Send payout via Checkbook.
                if amount_to_send > 0:
                    # Send one check for all orders.
                    check_response = Lob().sendPhysicalCheck(
                        seller_location=seller_location,
                        amount=amount_to_send,
                        orders=orders_for_seller_location,
                    )
                    if isinstance(check_response, CheckErrorResponse):
                        messages.error(
                            request,
                            f"""Checkbook error occurred:
                             [{check_response.status_code}]-{check_response.message} on
                             seller_location id: {str(seller_location.id)}. Please check BetterStack logs.""",
                        )
                    else:
                        # Save Payout for each order.
                        for order in orders_for_seller_location:
                            payout_diff = self.seller_price(
                                order
                            ) - self.total_paid_to_seller(order)
                            if payout_diff > 0:
                                payout = Payout(
                                    order=order,
                                    amount=payout_diff,
                                    lob_check_id=check_response.id,
                                )
                                if check_response.check_number:
                                    payout.check_number = check_response.check_number
                                payout.save()

        messages.success(request, "Successfully paid out all selected orders.")

    def send_supplier_approval_email(self, request, queryset):
        _cnt = 0
        for order in queryset:
            order.send_supplier_approval_email()
            _cnt += 1
        self.message_user(
            request, "Successfully sent %s supplier approval emails" % (_cnt)
        )

    def customer_price(self, obj):
        return round(obj.customer_price(), 2)

    def seller_price(self, obj):
        return round(obj.seller_price(), 2)

    def customer_invoiced(self, obj: Order):
        invoiced_order_line_items = obj.order_line_items.filter(
            stripe_invoice_line_item_id__isnull=False
        )

        total_invoiced = 0
        order_line_item: OrderLineItem
        for order_line_item in invoiced_order_line_items:
            total_invoiced += order_line_item.customer_price()
        return total_invoiced

    def customer_paid(self, obj):
        invoiced_order_line_items = obj.order_line_items.filter(
            stripe_invoice_line_item_id__isnull=False
        )

        total_paid = 0
        order_line_item: OrderLineItem
        for order_line_item in invoiced_order_line_items:
            total_paid += (
                order_line_item.customer_price()
                if order_line_item.payment_status() == OrderLineItem.PaymentStatus.PAID
                else 0
            )
        return total_paid

    def payment_status(self, obj):
        payout_diff = self.customer_invoiced(obj) - self.customer_paid(obj)
        if payout_diff == 0:
            return format_html("<p>&#128994;</p>")
        elif payout_diff > 0:
            return format_html("<p>&#128308;</p>")
        else:
            return format_html("<p>&#128993;</p>")

    def total_paid_to_seller(self, obj):
        payouts = Payout.objects.filter(order=obj)
        return sum([payout.amount for payout in payouts])

    def payout_status(self, obj):
        payout_diff = self.seller_price(obj) - self.total_paid_to_seller(obj)
        if payout_diff == 0:
            return format_html("<p>&#128994;</p>")
        elif payout_diff > 0:
            return format_html("<p>&#128993;</p>")
        else:
            return format_html("<p>&#128308;</p>")

    def total_invoiced_from_seller(self, obj):
        seller_invoice_payable_line_items = SellerInvoicePayableLineItem.objects.filter(
            order=obj
        )
        return sum(
            [
                seller_invoice_payable_line_items.amount
                for seller_invoice_payable_line_items in seller_invoice_payable_line_items
            ]
        )

    def seller_invoice_status(self, obj):
        payout_diff = self.total_invoiced_from_seller(obj) - self.total_paid_to_seller(
            obj
        )
        if payout_diff == 0 or self.total_invoiced_from_seller(obj) == 0:
            return format_html("<p>&#128994;</p>")
        elif payout_diff >= 0:
            return format_html("<p>&#128993;</p>")
        else:
            return format_html("<p>&#128308;</p>")
