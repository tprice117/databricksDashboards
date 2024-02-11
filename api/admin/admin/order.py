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
from api.utils.checkbook_io import CheckbookIO

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
    ]

    def auto_order_type(self, obj: Order):
        return obj.get_order_type()

    # @admin.action(description="Create draft invoices")
    # def create_draft_invoices(self, request, queryset):
    #     # Get distinct UserAddresses.
    #     distinct_user_addresses: List[UserAddress] = []
    #     for order in queryset:
    #         user_address = order.order_group.user_address
    #         current_user_address_ids = [
    #             user_address.id for user_address in distinct_user_addresses
    #         ]
    #         if user_address.id not in current_user_address_ids:
    #             distinct_user_addresses.append(user_address)

    #     # For each UserAddress, create or update invoices for all orders.
    #     for user_address in distinct_user_addresses:
    #         # Check if UserAddress has a Stripe Customer ID.
    #         # If not, create a Stripe Customer.
    #         if not user_address.stripe_customer_id:
    #             stripe_customer = stripe.Customer.create(
    #                 email=user_address.user.email,
    #                 name=user_address.name,
    #             )
    #             user_address.stripe_customer_id = stripe_customer.id
    #             user_address.save()

    #         orders_for_user_address = queryset.filter(
    #             order_group__user_address=user_address
    #         )

    #         # Get the current draft invoice or create a new one.
    #         draft_invoices = stripe.Invoice.search(
    #             query='customer:"'
    #             + user_address.stripe_customer_id
    #             + '" AND status:"draft"',
    #         )
    #         if len(draft_invoices) > 0:
    #             stripe_invoice = draft_invoices["data"][0]
    #         else:
    #             stripe_invoice = stripe.Invoice.create(
    #                 customer=user_address.stripe_customer_id,
    #                 auto_advance=False,
    #             )

    #         # Enable automatic taxes on the invoice.
    #         stripe.Invoice.modify(
    #             stripe_invoice.id,
    #             automatic_tax={
    #                 "enabled": True,
    #             },
    #         )

    #         # Loop through each order and add any OrderLineItems that don't have
    #         # a StripeInvoiceLineItemId on the OrderLineItem.
    #         order: Order
    #         for order in orders_for_user_address:
    #             # Get existing Stripe Invoice Summary Item(s) for this [Order].
    #             stripe_invoice_summary_items_response = requests.get(
    #                 "https://api.stripe.com/v1/invoices/"
    #                 + stripe_invoice.id
    #                 + "/summary_items",
    #                 headers={
    #                     "Authorization": "Bearer " + settings.STRIPE_SECRET_KEY,
    #                 },
    #             )
    #             stripe_invoice_summary_items = (
    #                 stripe_invoice_summary_items_response.json()["data"]
    #             )

    #             # Ensure we have a Stripe Invoice Summary Item for this [Order].
    #             # If order.stripe_invoice_summary_item_id is None, then create a new one.
    #             if any(
    #                 x["description"] == order.stripe_invoice_summary_item_description()
    #                 for x in stripe_invoice_summary_items
    #             ):
    #                 stripe_invoice_summary_item = next(
    #                     (
    #                         item
    #                         for item in stripe_invoice_summary_items
    #                         if item["description"]
    #                         == order.stripe_invoice_summary_item_description()
    #                     ),
    #                     None,
    #                 )
    #             else:
    #                 new_summary_invoice_summary_item_response = requests.post(
    #                     "https://api.stripe.com/v1/invoices/"
    #                     + stripe_invoice.id
    #                     + "/summary_items",
    #                     headers={
    #                         "Authorization": "Bearer " + settings.STRIPE_SECRET_KEY,
    #                         "Content-Type": "application/x-www-form-urlencoded",
    #                     },
    #                     data={
    #                         "description": order.stripe_invoice_summary_item_description(),
    #                     },
    #                 )
    #                 stripe_invoice_summary_item = (
    #                     new_summary_invoice_summary_item_response.json()
    #                 )

    #             # Get OrderLineItems that don't have a StripeInvoiceLineItemId.
    #             order_line_items = OrderLineItem.objects.filter(
    #                 order=order,
    #                 stripe_invoice_line_item_id=None,
    #             )

    #             # Create Stripe Invoice Line Item for each OrderLineItem that
    #             # doesn't have a StripeInvoiceLineItemId.
    #             order_line_item: OrderLineItem
    #             for order_line_item in order_line_items:
    #                 # Create Stripe Invoice Line Item.
    #                 stripe_invoice_line_item = stripe.InvoiceItem.create(
    #                     customer=order.order_group.user_address.stripe_customer_id,
    #                     invoice=stripe_invoice.id,
    #                     description=order_line_item.order_line_item_type.name
    #                     + " | Qty: "
    #                     + str(order_line_item.quantity)
    #                     + " @ $"
    #                     + (
    #                         str(
    #                             round(
    #                                 order_line_item.customer_price()
    #                                 / order_line_item.quantity,
    #                                 2,
    #                             )
    #                         )
    #                         if order_line_item.quantity > 0
    #                         else "0.00"
    #                     )
    #                     + "/unit",
    #                     amount=round(100 * order_line_item.customer_price()),
    #                     tax_behavior="exclusive",
    #                     tax_code=order_line_item.order_line_item_type.stripe_tax_code_id,
    #                     currency="usd",
    #                     period={
    #                         "start": calendar.timegm(order.start_date.timetuple()),
    #                         "end": calendar.timegm(order.end_date.timetuple()),
    #                     },
    #                     metadata={
    #                         "order_line_item_id": order_line_item.id,
    #                         "main_product_name": order.order_group.seller_product_seller_location.seller_product.product.main_product.name,
    #                         "order_start_date": order.start_date.strftime("%a, %b %-d"),
    #                         "order_end_date": order.end_date.strftime("%a, %b %-d"),
    #                     },
    #                 )

    #                 # Update OrderLineItem with StripeInvoiceLineItemId.
    #                 order_line_item.stripe_invoice_line_item_id = (
    #                     stripe_invoice_line_item.id
    #                 )
    #                 order_line_item.save()

    #                 # Get all Stripe Invoice Items for this Stripe Invoice.
    #                 stripe_invoice_items_response = requests.get(
    #                     f"https://api.stripe.com/v1/invoices/{stripe_invoice.id}/lines",
    #                     headers={
    #                         "Authorization": "Bearer " + settings.STRIPE_SECRET_KEY,
    #                     },
    #                 )

    #                 # Get the Stripe Invoice Item for this OrderLineItem.
    #                 stripe_invoice_items = stripe_invoice_items_response.json()["data"]
    #                 stripe_invoice_item = next(
    #                     (
    #                         item
    #                         for item in stripe_invoice_items
    #                         if item["metadata"]["order_line_item_id"]
    #                         and item["metadata"]["order_line_item_id"]
    #                         == str(order_line_item.id)
    #                     ),
    #                     None,
    #                 )

    #                 # Add Stripe Invoice Line Item to Stripe Invoice Summary Item.
    #                 if stripe_invoice_item:
    #                     response = requests.post(
    #                         f"https://api.stripe.com/v1/invoices/{stripe_invoice.id}/lines/{stripe_invoice_item['id']}",
    #                         headers={
    #                             "Authorization": "Bearer " + settings.STRIPE_SECRET_KEY,
    #                             "Content-Type": "application/x-www-form-urlencoded",
    #                         },
    #                         data={
    #                             "rendering[summary_item]": stripe_invoice_summary_item[
    #                                 "id"
    #                             ],
    #                         },
    #                     )
    #                     print(response.json())

    #     messages.success(
    #         request, "Successfully created/updated invoices for all selected orders."
    #     )

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
                    check_number = CheckbookIO().sendPhysicalCheck(
                        seller_location=seller_location,
                        amount=amount_to_send,
                        orders=orders_for_seller_location,
                    )

                # Save Payout for each order.
                for order in orders_for_seller_location:
                    payout_diff = self.seller_price(order) - self.total_paid_to_seller(
                        order
                    )
                    if payout_diff > 0:
                        Payout.objects.create(
                            order=order,
                            amount=payout_diff,
                            checkbook_payout_id=check_number,
                        )

        messages.success(request, "Successfully paid out all selected orders.")

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
