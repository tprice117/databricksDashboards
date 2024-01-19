import datetime
from decimal import Decimal
from typing import List

import stripe
from django.db.models import F, OuterRef, Q, Subquery, Sum
from django.db.models.functions import Round

from api.models.order.order import Order
from api.models.order.order_line_item import OrderLineItem
from api.models.payout import Payout
from api.models.seller.seller_invoice_payable_line_item import (
    SellerInvoicePayableLineItem,
)
from api.models.seller.seller_location import SellerLocation
from api.utils.checkbook_io import CheckbookIO
from common.utils.stripe import StripeUtils


class PayoutUtils:
    @staticmethod
    def send_payouts():
        # Get all Orders that are ready for payout.
        # Order.EndDate is 2 weeks ago or earlier.
        # Order.Status is "Complete".
        # orders = Order.objects.filter(
        #     end_date__lte=datetime.date.today() - datetime.timedelta(days=14),
        #     status=Order.COMPLETE,
        # )
        # print(len(orders))

        # # Filter Orders to only include Orders that need to be paid out.
        # order: Order
        # orders = [order for order in orders if order.needed_payout_to_seller() > 0]
        # print(len(orders))

        # # For Orders with SellerLocation.SendsInovices = True, filter out Orders
        # # where the Order.SellerPrice is not equal to the sum SellerInvoicePayableLineItems.
        # orders = [
        #     order
        #     for order in orders
        #     if not order.order_group.seller_product_seller_location.seller_location.sends_invoices
        #     or (
        #         order.order_group.seller_product_seller_location.seller_location.sends_invoices
        #         and SellerInvoicePayableLineItem.objects.filter(order=order).aggregate(
        #             Sum("amount")
        #         )["amount__sum"]
        #         == order.seller_price()
        #     )
        # ]

        orders = (
            Order.objects.filter(
                end_date__lte=datetime.date.today() - datetime.timedelta(days=14),
                status=Order.COMPLETE,
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
                total_seller_price=Round(
                    Sum(F("order_line_items__rate") * F("order_line_items__quantity")),
                    percision=2,
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

        # Filter Orders to only include Orders that need to be paid out.
        order: Order
        orders = [order for order in orders if order.needed_payout_to_seller() > 0]

        # for order in orders:
        #     print(
        #         str(order.id)
        #         + " | "
        #         + str((order.total_payouts or 0.00) - order.total_paid_to_seller())
        #         + " | "
        #         + str(order.total_seller_price - order.seller_price())
        #         + " | "
        #         + str(
        #             Decimal(order.total_needed_payout_to_seller or 0)
        #             - order.needed_payout_to_seller()
        #         )
        #         + " | "
        #         + str(order.needed_payout_to_seller())
        #     )
        print(len(orders))

        total = 0
        for order in orders:
            # print("$" + str(order.needed_payout_to_seller()))
            total += order.needed_payout_to_seller()
        print("TOTAL NEEDS TO BE PAID OUT: " + str(total))

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

        # For each SellerLocation, send payouts for all orders.
        for seller_location in distinct_seller_locations:
            orders_for_seller_location = [
                order
                for order in orders
                if order.order_group.seller_product_seller_location.seller_location
                == seller_location
            ]

            if PayoutUtils.can_send_stripe_payout(seller_location):
                # Send Stripe Payouts.
                for order in orders_for_seller_location:
                    PayoutUtils.send_stripe_payout(order)
            elif PayoutUtils.can_send_check_payout(seller_location):
                # Send Check Payouts.
                PayoutUtils.send_check_payout(
                    seller_location,
                    orders_for_seller_location,
                )
            else:
                # Print error message.
                print("Cannot send payouts for SellerLocation: " + seller_location.name)

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
    def send_stripe_payout(order: Order):
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
                # transfer = StripeUtils.Transfer.create(
                #     amount=round(order.needed_payout_to_seller() * 100),
                #     currency="usd",
                #     destination=order.order_group.seller_product_seller_location.seller_location.stripe_connect_account_id,
                # )

                # # Save Payout.
                # return Payout.objects.create(
                #     order=order,
                #     amount=order.needed_payout_to_seller(),
                #     stripe_transfer_id=transfer.id,
                # )
            except stripe.error.StripeError as stripe_error:
                print("Stripe error occurred:", stripe_error)
                return None
            except Exception as ex:
                print("Unhandled (non-Stripe) error occurred: " + str(ex))
                return None

    @staticmethod
    def send_check_payout(
        seller_location: SellerLocation,
        orders: List[Order],
    ):
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
            #     check_number = CheckbookIO().sendPhysicalCheck(
            #         seller_location=seller_location,
            #         amount=amount_to_send,
            #         orders=orders,
            #     )

            # # Save Payout for each order.
            # for order in orders:
            #     Payout.objects.create(
            #         order=order,
            #         amount=order.needed_payout_to_seller(),
            #         checkbook_payout_id=check_number,
            #     )
