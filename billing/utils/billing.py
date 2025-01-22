import calendar
import datetime
import logging
import re
from typing import Iterable, List

import stripe
from django.conf import settings
from django.utils import timezone

from api.models import Order, OrderLineItem, UserAddress, UserGroup
from api.models.order.common.order_item import OrderItem
from common.utils.get_last_day_of_previous_month import get_last_day_of_previous_month
from common.utils.stripe.stripe_utils import StripeUtils
from notifications.utils.add_email_to_queue import add_internal_email_to_queue

from .utils import Utils

logger = logging.getLogger(__name__)


class BillingUtils:
    @staticmethod
    def create_invoice_items_for_order(invoice: stripe.Invoice, order: Order):
        # Check that the Stripe Invoice Customer is the same as the
        # Order UserAddress Stripe Customer.
        if invoice.customer != order.order_group.user_address.stripe_customer_id:
            raise Exception(
                "Stripe Invoice Customer must be the same as the Order UserAddress Stripe Customer."
            )

        try:
            # Ensure we have a Stripe Invoice Summary Item for this [Order].
            # If order.stripe_invoice_summary_item_id is None, then create a new one.
            description, expanded_description = (
                order.stripe_invoice_summary_item_description()
            )
            stripe_invoice_summary_item = (
                StripeUtils.SummaryItems.get_or_create_by_description(
                    invoice, description, expanded_description
                )
            )

            # Get OrderLineItems that don't have a StripeInvoiceLineItemId.
            order_line_items = OrderLineItem.objects.filter(
                order=order,
                stripe_invoice_line_item_id=None,
            )

            # Create Stripe Invoice Line Item for each OrderLineItem that
            # doesn't have a StripeInvoiceLineItemId.
            order_line_item: OrderLineItem
            order_line_item_ids = []
            for order_line_item in order_line_items:
                order_line_item_ids.append(str(order_line_item.id))
                # Create Stripe Invoice Line Item.
                description = (
                    order_line_item.order_line_item_type.name
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
                    + "/unit"
                )
                try:
                    description = order_line_item.stripe_description
                except Exception as e:
                    logger.error(
                        f"BillingUtils.create_invoice_items_for_order: [line_item: {order_line_item.id}]-[{e}]",
                        exc_info=e,
                    )
                stripe_invoice_item = stripe.InvoiceItem.create(
                    customer=order.order_group.user_address.stripe_customer_id,
                    invoice=invoice.id,
                    description=description,
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
                order_line_item.stripe_invoice_line_item_id = stripe_invoice_item.id
                order_line_item.save()

            # Create Stripe Invoice Line Item for each OrderItem that
            # doesn't have a StripeInvoiceLineItemId.
            non_zero_order_items = [
                order_item
                for order_item in order.order_items
                if order_item.customer_rate != 0
                and not order_item.stripe_invoice_line_item_id
            ]

            order_item: OrderItem
            order_item_ids = []
            for order_item in non_zero_order_items:
                order_item_ids.append(str(order_item.id))

                # Get the "human readable" name of the model.
                model_name = type(order_item).__name__
                human_readable_name = " ".join(
                    word for word in re.findall(r"[A-Z][a-z]*", model_name)
                )
                human_readable_name = human_readable_name.replace("Order", "")

                # Create Stripe Invoice Line Item.
                description = f"{human_readable_name}"  # {f' | {order_item.description}' if order_item.description else ''}"

                stripe_invoice_item = stripe.InvoiceItem.create(
                    customer=order.order_group.user_address.stripe_customer_id,
                    invoice=invoice.id,
                    description=description,
                    quantity=round(order_item.quantity),
                    unit_amount=round(100 * order_item.customer_rate),
                    tax_behavior="exclusive",
                    tax_code=order_item.stripe_tax_code_id,
                    currency="usd",
                    period={
                        "start": calendar.timegm(order.start_date.timetuple()),
                        "end": calendar.timegm(order.end_date.timetuple()),
                    },
                    metadata={
                        "order_line_item_id": order_item.id,
                        "main_product_name": order.order_group.seller_product_seller_location.seller_product.product.main_product.name,
                        "order_start_date": order.start_date.strftime("%a, %b %-d"),
                        "order_end_date": order.end_date.strftime("%a, %b %-d"),
                    },
                )

                # Update OrderLineItem with StripeInvoiceLineItemId.
                order_item.stripe_invoice_line_item_id = stripe_invoice_item.id
                order_item.save()

            # Get all Stripe Invoice Items for this Stripe Invoice.
            stripe_invoice_line_items = StripeUtils.InvoiceLineItem.get_all_for_invoice(
                invoice_id=invoice.id,
            )

            stripe_invoice_line_item_subset = []
            for order_line_item_id in order_line_item_ids:
                # Get the Stripe Invoice Item for this OrderLineItem.
                stripe_invoice_line_item_subset.extend(
                    [
                        item
                        for item in stripe_invoice_line_items
                        if item["metadata"]["order_line_item_id"]
                        and item["metadata"]["order_line_item_id"] == order_line_item_id
                    ]
                )

            # Add Stripe Invoice Line Item to Stripe Invoice Summary Item.
            if stripe_invoice_line_item_subset:
                invoice = (
                    StripeUtils.SummaryItems.add_invoice_item_to_summary_item_bulk(
                        invoice=invoice,
                        invoice_line_items=stripe_invoice_line_item_subset,
                        invoice_summary_item_id=stripe_invoice_summary_item["id"],
                    )
                )

                # print(invoice)
            # Update all of the line items to ensure the tax is correct.
            order.update_line_items_tax()
        except Exception as e:
            print(e)
            logger.error(
                f"BillingUtils.create_invoice_items_for_order: [{e}]", exc_info=e
            )
        return invoice

    @staticmethod
    def create_stripe_invoice_for_user_address(
        orders: List[Order],
        user_address: UserAddress,
        is_cart=False,
        is_booking=False,
    ) -> stripe.Invoice:
        # Validation: Ensure all orders are for the same user address.
        if not all(order.order_group.user_address == user_address for order in orders):
            raise Exception("All orders must be for the same user address.")

        # Get the current draft invoice or create a new one.
        invoice = BillingUtils.get_or_create_invoice_for_user_address(
            user_address,
            is_cart=is_cart,
            is_booking=is_booking,
        )

        # Loop through each order and add any OrderLineItems that don't have
        # a StripeInvoiceLineItemId on the OrderLineItem.
        order: Order
        for order in orders:
            invoice = BillingUtils.create_invoice_items_for_order(
                invoice=invoice,
                order=order,
            )

        return invoice

    @staticmethod
    def create_stripe_invoice_for_cart(
        user_address: UserAddress, orders: Iterable[Order], raise_error: bool = False
    ):
        """
        Create Stripe Invoice for all Orders that are passed in for the UserAddress.
        """
        # Filter Orders. Only include Orders that have not been fully invoiced.
        orders = [
            order for order in orders if not order.all_order_line_items_invoiced()
        ]

        if not orders:
            return True, None

        # Get the current draft invoice or create a new one.
        invoice = BillingUtils.create_stripe_invoice_for_user_address(
            orders=orders,
            user_address=user_address,
            is_cart=True,
        )
        invoice_id = invoice.id

        # Finalize the invoice.
        is_paid, invoice = BillingUtils.finalize_and_pay_stripe_invoice(
            invoice=invoice,
            user_group=user_address.user_group,
            autopay=True,
            raise_error=raise_error,
        )
        if not is_paid:
            stripe.Invoice.void_invoice(invoice_id)
            for order in orders:
                order.order_line_items.all().update(stripe_invoice_line_item_id=None)
        return is_paid, invoice

    @staticmethod
    def create_stripe_invoices_for_user_group(
        user_group: UserGroup,
        end_date_lte: datetime = datetime.date.today(),
    ):
        """
        Create Stripe Invoices for all Orders that have been completed and have an end date on
        or before either (a) yesterday (default) or (b) the date specified by the end_date_lte.
        """
        # Get all Orders that have been completed and have an end date on
        # or before the last day of the previous month.
        orders = Order.objects.filter(
            status="COMPLETE",
            end_date__lte=end_date_lte,
            order_group__user_address__user_group=user_group,
        )

        # Filter Orders. Only include Orders that have not been fully invoiced.
        orders = [
            order for order in orders if not order.all_order_line_items_invoiced()
        ]

        # Get distinct UserAddresses.
        distinct_user_addresses = {order.order_group.user_address for order in orders}

        # For each UserAddress, create or update invoices for all orders.
        user_address: UserAddress
        for user_address in distinct_user_addresses:
            orders_for_user_address = [
                order
                for order in orders
                if order.order_group.user_address == user_address
            ]

            # Get the current draft invoice or create a new one.
            invoice = BillingUtils.create_stripe_invoice_for_user_address(
                orders=orders_for_user_address,
                user_address=user_address,
            )

            # Finalize the invoice.
            BillingUtils.finalize_and_pay_stripe_invoice(
                invoice=invoice,
                user_group=user_group,
            )

    @staticmethod
    def create_stripe_invoices_for_previous_month(finalize_and_pay: bool):
        # Get all Orders that have been completed and have an end date on
        # or before the last day of the previous month. Also, exclude orders
        # that have a UserGroup with an invoice_day_of_month set (means we
        # will create invoices "off-cycle" for these orders later in the month when the
        # invoice_day_of_month is reached).
        orders = Order.objects.filter(
            status="COMPLETE",
            end_date__lte=get_last_day_of_previous_month(),
            order_group__user_address__user_group__invoice_day_of_month__isnull=True,
        )

        # Get distinct UserAddresses.
        distinct_user_addresses = {order.order_group.user_address for order in orders}

        # For each UserAddress, create or update invoices for all orders.
        user_address: UserAddress
        for user_address in distinct_user_addresses:
            orders_for_user_address = orders.filter(
                order_group__user_address=user_address
            )

            # Create invoice for user address.
            invoice = BillingUtils.create_stripe_invoice_for_user_address(
                orders=orders_for_user_address,
                user_address=user_address,
            )

            # If finalize_and_pay is True, finalize the invoice and attempt
            # to pay it.
            if finalize_and_pay:
                BillingUtils.finalize_and_pay_stripe_invoice(
                    invoice=invoice,
                    user_group=user_address.user_group,
                )

    @staticmethod
    def get_or_create_invoice_for_user_address(
        user_address: UserAddress, is_cart=False, is_booking=False
    ):
        """
        Get the current draft invoice or create a new one. Also,
        enable automatic taxes on the invoice (if not already enabled).
        """
        # Get the current draft invoice or create a new one.
        query = 'customer:"' + user_address.stripe_customer_id + '" AND status:"draft"'
        if is_cart:
            query = f'{query} AND metadata["cart_invoice"]:"True"'
        elif is_booking:
            query = f'{query} AND metadata["booking_invoice"]:"True"'
        draft_invoices = stripe.Invoice.search(query=query)

        # Should taxes be collected for this customer?
        collect_tax = (
            user_address.user_group.tax_exempt_status
            != UserGroup.TaxExemptStatus.EXEMPT
            if user_address.user_group
            else True
        )
        custom_fields = []
        if user_address.project_id:
            custom_fields = [
                {
                    "name": "project_id",
                    "value": user_address.project_id,
                }
            ]

        if len(draft_invoices) > 0:
            stripe_invoice = draft_invoices["data"][0]

            # Ensure automatic taxes are set correctly.
            stripe_invoice = stripe.Invoice.modify(
                stripe_invoice.id,
                automatic_tax={
                    "enabled": collect_tax,
                },
                custom_fields=custom_fields,
            )
        else:
            stripe_invoice = stripe.Invoice.create(
                customer=user_address.stripe_customer_id,
                auto_advance=user_address.autopay,
                collection_method="send_invoice",
                days_until_due=(
                    user_address.user_group.net_terms if user_address.user_group else 0
                ),
                automatic_tax={
                    "enabled": collect_tax,
                },
                custom_fields=custom_fields,
            )

        return stripe_invoice

    @staticmethod
    def finalize_and_pay_stripe_invoice(
        invoice: stripe.Invoice,
        user_group: UserGroup,
        send_invoice: bool = True,
        autopay: bool = False,
        raise_error: bool = False,
    ):
        """
        Finalizes and pays a Stripe Invoice for a UserGroup.
        """
        # Finalize the invoice.
        StripeUtils.Invoice.finalize(invoice.id)

        # If autopay is enabled, pay the invoice.
        # This should respect the due date of the invoice.
        is_paid = False
        if (
            user_group.autopay and invoice["due_date"] <= timezone.now().timestamp()
        ) or autopay:
            try:
                is_paid, invoice = StripeUtils.Invoice.attempt_pay(
                    invoice.id, raise_error=raise_error
                )
            except Exception as e:
                print("Attempt pay error: ", e)
                logger.error(
                    f"BillingUtils.finalize_and_pay_stripe_invoice: [Attempt Pay]-[{e}]",
                    exc_info=e,
                )

        # Send the invoice.
        if send_invoice:
            try:
                StripeUtils.Invoice.send_invoice(invoice.id)
            except Exception as e:
                print("Send invoice error: ", e)
                logger.error(
                    f"BillingUtils.finalize_and_pay_stripe_invoice: [Send Invoice]-[{e}]",
                    exc_info=e,
                )

        return is_paid, invoice

    @staticmethod
    def run_interval_based_invoicing():
        """
        Runs invoices for all UserGroups based on the UserGroup's invoice frequency.
        """
        # Capture if the task failed.
        failed = False
        error_messages = []

        try:
            # Get all UserGroups that need to be invoiced.
            user_groups = UserGroup.objects.all()

            for user_group in user_groups:
                if Utils.is_user_groups_invoice_date(user_group):
                    BillingUtils.create_stripe_invoices_for_user_group(user_group)
        except Exception as e:
            print(e)
            logger.error(
                f"BillingUtils.run_interval_based_invoicing: [{e}]", exc_info=e
            )
            failed = True
            error_messages.append(str(e))
            error_messages.append("--------------")

        # If the task failed, send an email to the admin.
        if settings.ENVIRONMENT == "TEST":
            add_internal_email_to_queue(
                from_email="system@trydownstream.com",
                subject=(
                    f"Interval-based Invoicing {'Failed' if failed else 'Succeeded'}"
                ),
                additional_to_emails=[
                    "lgeber@trydownstream.com",
                ],
                html_content=(
                    f"<p>Interval-based invoicing task has {'failed' if failed else 'succeeded'}.</p>"
                    + "<p>Error messages:</p>"
                    + "<p>"
                    + "<br>".join(error_messages)
                    + "</p>"
                ),
            )

    @staticmethod
    def run_project_end_based_invoicing():
        """
        Runs invoices for all UserAddresses that have no active projects.
        """
        # Capture if the task failed.
        failed = False

        # Get all UserAddresses that need to be invoiced.
        try:
            user_addresses = UserAddress.objects.filter(
                user_group__invoice_at_project_completion=True,
            )

            for user_address in user_addresses:
                if Utils.is_user_address_project_complete_and_needs_invoice(
                    user_address
                ):
                    # Get all Orders that have been completed and have an end date on
                    # or before the last day of the previous month.
                    orders = Order.objects.filter(
                        status="COMPLETE",
                        end_date__lte=datetime.date.today(),
                        order_group__user_address=user_address,
                    )

                    # Filter Orders. Only include Orders that have not been fully invoiced.
                    orders = [
                        order
                        for order in orders
                        if not order.all_order_line_items_invoiced()
                    ]
                    # Only create an invoice if there are orders to invoice.
                    if orders:
                        invoice = BillingUtils.create_stripe_invoice_for_user_address(
                            orders,
                            user_address,
                        )

                        # Finalize the invoice.
                        BillingUtils.finalize_and_pay_stripe_invoice(
                            invoice=invoice,
                            user_group=user_address.user_group,
                        )
        except Exception as e:
            logger.error(
                f"BillingUtils.run_project_end_based_invoicing: [{e}]", exc_info=e
            )
            failed = True

        # If the task failed, send an email to the admin.
        add_internal_email_to_queue(
            from_email="system@trydownstream.com",
            subject=(f"Project-based Invoicing {'Failed' if failed else 'Succeeded'}"),
            additional_to_emails=[
                "lgeber@trydownstream.com",
            ],
            html_content=(
                f"<p>Project-based invoicing task has {'failed' if failed else 'succeeded'}.</p>"
            ),
        )
