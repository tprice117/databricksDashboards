import calendar
from typing import List

import requests
import stripe
from django.conf import settings

from api.models import Order, OrderLineItem, UserAddress
from common.utils.get_last_day_of_previous_month import get_last_day_of_previous_month

stripe.api_key = settings.STRIPE_SECRET_KEY


def create_stripe_invoices():
    print("create_stripe_invoices")
    return

    # Get all Orders that have been completed and have an end date on
    # or before the last day of the previous month.
    orders = Order.objects.filter(
        status="COMPLETE",
        end_date__lte=get_last_day_of_previous_month(),
    )

    # Get distinct UserAddresses.
    distinct_user_addresses: List[UserAddress] = []
    for order in orders:
        user_address = order.order_group.user_address
        current_user_address_ids = [
            user_address.id for user_address in distinct_user_addresses
        ]
        if user_address.id not in current_user_address_ids:
            distinct_user_addresses.append(user_address)

    # For each UserAddress, create or update invoices for all orders.
    user_address: UserAddress
    for user_address in distinct_user_addresses:
        orders_for_user_address = orders.filter(order_group__user_address=user_address)

        # Get the current draft invoice or create a new one.
        draft_invoices = stripe.Invoice.search(
            query='customer:"'
            + user_address.stripe_customer_id
            + '" AND status:"draft"',
        )
        if len(draft_invoices) > 0:
            stripe_invoice = draft_invoices["data"][0]
        else:
            stripe_invoice = stripe.Invoice.create(
                customer=user_address.stripe_customer_id,
                auto_advance=user_address.autopay,
            )

        # Enable automatic taxes on the invoice.
        stripe.Invoice.modify(
            stripe_invoice.id,
            automatic_tax={
                "enabled": True,
            },
        )

        # Loop through each order and add any OrderLineItems that don't have
        # a StripeInvoiceLineItemId on the OrderLineItem.
        order: Order
        for order in orders_for_user_address:
            try:
                # Get existing Stripe Invoice Summary Item(s) for this [Order].
                stripe_invoice_summary_items_response = requests.get(
                    "https://api.stripe.com/v1/invoices/"
                    + stripe_invoice.id
                    + "/summary_items",
                    headers={
                        "Authorization": "Bearer " + settings.STRIPE_SECRET_KEY,
                    },
                )
                stripe_invoice_summary_items = (
                    stripe_invoice_summary_items_response.json()["data"]
                )

                # Ensure we have a Stripe Invoice Summary Item for this [Order].
                # If order.stripe_invoice_summary_item_id is None, then create a new one.
                if any(
                    x["description"] == order.stripe_invoice_summary_item_description()
                    for x in stripe_invoice_summary_items
                ):
                    stripe_invoice_summary_item = next(
                        (
                            item
                            for item in stripe_invoice_summary_items
                            if item["description"]
                            == order.stripe_invoice_summary_item_description()
                        ),
                        None,
                    )
                else:
                    new_summary_invoice_summary_item_response = requests.post(
                        "https://api.stripe.com/v1/invoices/"
                        + stripe_invoice.id
                        + "/summary_items",
                        headers={
                            "Authorization": "Bearer " + settings.STRIPE_SECRET_KEY,
                            "Content-Type": "application/x-www-form-urlencoded",
                        },
                        data={
                            "description": order.stripe_invoice_summary_item_description(),
                        },
                    )
                    stripe_invoice_summary_item = (
                        new_summary_invoice_summary_item_response.json()
                    )

                # Get OrderLineItems that don't have a StripeInvoiceLineItemId.
                order_line_items = OrderLineItem.objects.filter(
                    order=order,
                    stripe_invoice_line_item_id=None,
                )

                # Create Stripe Invoice Line Item for each OrderLineItem that
                # doesn't have a StripeInvoiceLineItemId.
                order_line_item: OrderLineItem
                for order_line_item in order_line_items:
                    # Create Stripe Invoice Line Item.
                    stripe_invoice_line_item = stripe.InvoiceItem.create(
                        customer=order.order_group.user_address.stripe_customer_id,
                        invoice=stripe_invoice.id,
                        description=order_line_item.order_line_item_type.name
                        + " | Qty: "
                        + str(order_line_item.quantity)
                        + " @ $"
                        + (
                            str(
                                round(
                                    order_line_item.customer_price()
                                    / order_line_item.quantity,
                                    2,
                                )
                            )
                            if order_line_item.quantity > 0
                            else "0.00"
                        )
                        + "/unit",
                        amount=round(100 * order_line_item.customer_price()),
                        tax_behavior="exclusive",
                        tax_code=order_line_item.order_line_item_type.stripe_tax_code_id,
                        currency="usd",
                        period={
                            "start": calendar.timegm(order.start_date.timetuple()),
                            "end": calendar.timegm(order.end_date.timetuple()),
                        },
                        metadata={
                            "order_line_item_id": order_line_item.id,
                            "main_product_name": order.order_group.seller_product_seller_location.seller_product.product.main_product.name,
                            "order_start_date": order.start_date.strftime("%a, %b %-d"),
                            "order_end_date": order.end_date.strftime("%a, %b %-d"),
                        },
                    )

                    # Update OrderLineItem with StripeInvoiceLineItemId.
                    order_line_item.stripe_invoice_line_item_id = (
                        stripe_invoice_line_item.id
                    )
                    order_line_item.save()

                    # Get all Stripe Invoice Items for this Stripe Invoice.
                    stripe_invoice_items_response = requests.get(
                        f"https://api.stripe.com/v1/invoices/{stripe_invoice.id}/lines",
                        headers={
                            "Authorization": "Bearer " + settings.STRIPE_SECRET_KEY,
                        },
                    )

                    # Get the Stripe Invoice Item for this OrderLineItem.
                    stripe_invoice_items = stripe_invoice_items_response.json()["data"]
                    stripe_invoice_item = next(
                        (
                            item
                            for item in stripe_invoice_items
                            if item["metadata"]["order_line_item_id"]
                            and item["metadata"]["order_line_item_id"]
                            == str(order_line_item.id)
                        ),
                        None,
                    )

                    # Add Stripe Invoice Line Item to Stripe Invoice Summary Item.
                    if stripe_invoice_item:
                        response = requests.post(
                            f"https://api.stripe.com/v1/invoices/{stripe_invoice.id}/lines/{stripe_invoice_item['id']}",
                            headers={
                                "Authorization": "Bearer " + settings.STRIPE_SECRET_KEY,
                                "Content-Type": "application/x-www-form-urlencoded",
                            },
                            data={
                                "rendering[summary_item]": stripe_invoice_summary_item[
                                    "id"
                                ],
                            },
                        )
                        print(response.json())
            except Exception as e:
                print(e)
                pass
