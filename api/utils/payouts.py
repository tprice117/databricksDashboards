import datetime
from decimal import Decimal
from typing import List, Union

import stripe
from django.conf import settings
from django.db.models import DecimalField, F, Func, OuterRef, Q, Subquery, Sum
from django.db.models.functions import Round
from django.template.loader import render_to_string
import logging

from api.models.order.order import Order
from api.models.order.order_line_item import OrderLineItem
from api.models.payout import Payout
from api.models.seller.seller_invoice_payable_line_item import (
    SellerInvoicePayableLineItem,
)
from api.models.seller.seller_location import SellerLocation
from api.utils.lob import Lob, CheckErrorResponse
from common.utils.stripe.stripe_utils import StripeUtils
from notifications.utils.add_email_to_queue import add_internal_email_to_queue

logger = logging.getLogger(__name__)


class PayoutUtils:
    @staticmethod
    def send_payouts():
        orders = PayoutUtils.get_orders_that_need_to_be_paid_out()

        # Filter Orders to only include Orders that need to be paid out.
        # The query above should already filter out Orders that don't
        # need to be paid out, but this is a "double check" to ensure
        # that we don't send payouts for Orders that don't need to be
        # paid out.
        order: Order
        orders = [order for order in orders if order.needed_payout_to_seller() > 0]

        # With the remaining Orders (that are ready for payout), create Payouts.
        # Get distinct SellerLocations.
        distinct_seller_location_ids: List[SellerLocation] = set(
            [
                order.order_group.seller_product_seller_location.seller_location.id
                for order in orders
            ]
        )
        distinct_seller_locations = SellerLocation.objects.filter(
            id__in=distinct_seller_location_ids
        )

        # Capture SellerLocation, Stripe or Checkbook, "Missing Payout Information" (only if applicable
        # if we can't send a payout for a SellerLocation due to missing information), Payouts (if any),
        # and Total Payout Amount.
        email_report_datas = []

        # For each SellerLocation, send payouts for all orders.
        for seller_location in distinct_seller_locations:
            orders_for_seller_location = [
                order
                for order in orders
                if order.order_group.seller_product_seller_location.seller_location
                == seller_location
            ]

            email_report_data = {
                "seller_location": seller_location,
                "payouts": [],
                "error": None,
            }

            if PayoutUtils.can_send_stripe_payout(seller_location):
                # Send Stripe Payouts.
                for order in orders_for_seller_location:
                    payout = PayoutUtils.send_stripe_payout(order)

                    # Add Payout to email report data.
                    if payout:
                        email_report_data["payouts"].append(payout)

            elif PayoutUtils.can_send_check_payout(seller_location):
                try:
                    # Send Check Payouts.
                    payout_response = PayoutUtils.send_check_payout(
                        seller_location,
                        orders_for_seller_location,
                    )
                    if payout_response:
                        if isinstance(payout_response, CheckErrorResponse):
                            # If there was an error sending the check, add error message to email report data.
                            email_report_data[
                                "error"
                            ] = f"""Checkbook error occurred:
                             [{payout_response.status_code}]-{payout_response.message} on
                             seller_location id: {str(seller_location.id)}. Please check BetterStack logs."""
                        else:
                            # If the check was sent successfully, add payouts to email report data.
                            email_report_data["payouts"] = payout_response
                except Exception as e:
                    logger.error(
                        f"PayoutUtils.send_payouts: [Unhandled (Checkbook)]-[{e}]",
                        exc_info=e,
                    )
                    email_report_data[
                        "error"
                    ] = f"""Unhandled (Checkbook) error occurred: {e} on
                     seller_location id: {str(seller_location.id)}. Please check BetterStack logs."""
            else:
                # Print error message.
                print("Cannot send payouts for SellerLocation: " + seller_location.name)

                # Add error message to email report data.
                email_report_data["missing_payout_information"] = True

            # Add email report data to list of email report datas.
            email_report_datas.append(email_report_data)

        # Send email report (only in PROD environment, not in DEV).
        if settings.ENVIRONMENT == "TEST":
            PayoutUtils._send_email_report(email_report_datas)

    @staticmethod
    def get_orders_that_need_to_be_paid_out():
        """
        Gets all Orders that need to be paid out.
        Filters:
        - Order.EndDate is 2 weeks ago or earlier.
        - Order.Status is "Complete".
        - Order.TotalNeededPayoutToSeller is greater than 0.
        - SellerLocation.SendsInvoices is False or
          SellerLocation.SendsInvoices is True and
          Order.TotalSellerPrice is equal to Order.TotalInvoicePayouts.
        """
        return (
            Order.objects.filter(
                end_date__lte=datetime.date.today() - datetime.timedelta(days=14),
                status=Order.Status.COMPLETE,
            )
            .annotate(
                total_payouts=Round(
                    Subquery(
                        Payout.objects.filter(order=OuterRef("pk"))
                        .values("order")
                        .annotate(total_payout_for_order=Sum("amount"))
                        .values("total_payout_for_order")[:1]
                    ),
                    percision=2,
                ),
                total_seller_price=Sum(
                    Func(
                        F("order_line_items__rate") * F("order_line_items__quantity"),
                        2,
                        function="ROUND",
                        output_field=DecimalField(),
                    )
                ),
                seller_location_sends_invoices=F(
                    "order_group__seller_product_seller_location__seller_location__sends_invoices"
                ),
                total_invoice_payouts=Subquery(
                    SellerInvoicePayableLineItem.objects.filter(order=OuterRef("pk"))
                    .values("order")
                    .annotate(total_invoice_payout_for_order=Sum("amount"))
                    .values("total_invoice_payout_for_order")[:1]
                ),
                total_needed_payout_to_seller=Round(
                    F("total_seller_price") - F("total_payouts"),
                    percision=2,
                ),
            )
            .filter(
                (
                    Q(total_needed_payout_to_seller=None)
                    | Q(total_needed_payout_to_seller__gt=0)
                )
                & (
                    Q(seller_location_sends_invoices=False)
                    | Q(
                        seller_location_sends_invoices=True,
                        total_seller_price=F("total_invoice_payouts"),
                    )
                )
            )
        )

    @staticmethod
    def can_send_stripe_payout(seller_location: SellerLocation) -> bool:
        return seller_location.stripe_connect_account_id

    @staticmethod
    def can_send_check_payout(seller_location: SellerLocation) -> bool:
        return seller_location.payee_name and hasattr(
            seller_location,
            "mailing_address",
        )

    @staticmethod
    def send_stripe_payout(order: Order) -> Payout:
        can_send_stripe_payout = PayoutUtils.can_send_stripe_payout(
            order.order_group.seller_product_seller_location.seller_location
        )

        if not can_send_stripe_payout:
            # If customer does not have a Stripe Customer ID, return None.
            return None
        else:
            # If customer does have a Stripe Customer ID, payout via Stripe.
            try:
                print(
                    "Stripe   "
                    + " | "
                    + str(
                        order.order_group.seller_product_seller_location.seller_location.id
                    )
                    + " | "
                    + str(order.id)
                    + " | "
                    + str(order.needed_payout_to_seller())
                    + " | "
                    + order.order_group.seller_product_seller_location.seller_location.seller.name
                )
                # Payout via Stripe.
                transfer = StripeUtils.Transfer.create(
                    amount=round(order.needed_payout_to_seller() * 100),
                    currency="usd",
                    destination=order.order_group.seller_product_seller_location.seller_location.stripe_connect_account_id,
                )

                # Save Payout.
                return Payout.objects.create(
                    order=order,
                    amount=order.needed_payout_to_seller(),
                    stripe_transfer_id=transfer.id,
                )
            except stripe.error.StripeError as stripe_error:
                print("Stripe error occurred:", stripe_error)
                logger.error(
                    f"Price_Model.predict_price: [Stripe]-[{stripe_error}]",
                    exc_info=stripe_error,
                )
                return None
            except Exception as ex:
                print("Unhandled (non-Stripe) error occurred: " + str(ex))
                logger.error(
                    f"Price_Model.predict_price: [Unhandled (non-Stripe)]-[{ex}]",
                    exc_info=ex,
                )
                return None

    @staticmethod
    def send_check_payout(
        seller_location: SellerLocation,
        orders: List[Order],
    ) -> Union[List[Payout], CheckErrorResponse, None]:
        # Check if SellerLocation has the information to send a check.
        can_send_check = PayoutUtils.can_send_check_payout(seller_location)

        if not can_send_check:
            # If billing info is not complete, return None.
            return None
        else:
            # If billing info is complete, send Payouts via Checkbook.
            # If not connected with Stripe Connect, but [payee_name] and
            # [mailing_address] are set, payout via Checkbook.
            amount_to_send = 0

            # Compute total amount to be sent.
            order: Order
            for order in orders:
                amount_to_send += order.needed_payout_to_seller()

            # Send payout via Checkbook.
            if amount_to_send > 0:
                print(
                    "Checkbook"
                    + " | "
                    + str(
                        order.order_group.seller_product_seller_location.seller_location.id
                    )
                    + " | "
                    + str(seller_location.id)
                    + " | "
                    + str(amount_to_send)
                    + " | "
                    + order.order_group.seller_product_seller_location.seller_location.seller.name
                )
                # Send one check for all orders.
                check_response = Lob().sendPhysicalCheck(
                    seller_location=seller_location,
                    amount=amount_to_send,
                    orders=orders,
                )

                if isinstance(check_response, CheckErrorResponse):
                    # If there was an error sending the check, return None.
                    return check_response
                else:
                    # Save Payout for each order.
                    payouts = []
                    for order in orders:
                        payout = Payout(
                            order=order,
                            amount=order.needed_payout_to_seller(),
                            lob_check_id=check_response.id,
                        )
                        if check_response.check_number:
                            payout.check_number = check_response.check_number
                        payout.save()
                        payouts.append(payout)

                    return payouts
            else:
                return None

    @staticmethod
    def _send_email_report(email_report_datas):
        print(email_report_datas)
        # Total payout data.
        total_paid = 0
        total_count = 0

        # Stripe payout data.
        stripe_total_paid = 0
        stripe_total_count = 0

        # Checkbook payout data.
        checkbook_total_paid = 0
        checkbook_total_count = 0

        # Errors encountered.
        errors = []

        # "Could not send payouts" data.
        number_of_seller_locations_missing_payout_information = 0

        for email_report_data in email_report_datas:
            total_count += len(email_report_data["payouts"])
            if email_report_data.get("error", None) is not None:
                errors.append(email_report_data["error"])

            # Loop through Payouts and add to Stripe or Checkbook totals.
            payout: Payout
            for payout in email_report_data["payouts"]:
                if payout.stripe_transfer_id:
                    total_paid += payout.amount
                    stripe_total_paid += payout.amount
                    stripe_total_count += 1
                elif payout.is_check:
                    total_paid += payout.amount
                    checkbook_total_paid += payout.amount
                    checkbook_total_count += 1

            # Add to "Could not send payouts" data.
            if email_report_data.get("missing_payout_information"):
                number_of_seller_locations_missing_payout_information += 1

        # Send email report.
        add_internal_email_to_queue(
            from_email="system@trydownstream.com",
            subject=f"Payout Batch Report: ${total_paid}",
            additional_to_emails=[
                "lgeber@trydownstream.com",
            ],
            html_content=render_to_string(
                "emails/internal/payout_batch_report.html",
                {
                    "seller_locations": email_report_datas,
                    "total": {
                        "paid": total_paid,
                        "count": total_count,
                    },
                    "stripe": {
                        "paid": stripe_total_paid,
                        "count": stripe_total_count,
                    },
                    "checkbook": {
                        "paid": checkbook_total_paid,
                        "count": checkbook_total_count,
                    },
                    "errors": errors,
                },
            ),
        )
