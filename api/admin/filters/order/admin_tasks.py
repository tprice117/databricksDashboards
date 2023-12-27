from django.contrib.admin import SimpleListFilter
from django.db.models import Sum

from api.models import Order, OrderLineItem


class OrderAdminTasksFilter(SimpleListFilter):
    title = "Admin Tasks"
    parameter_name = "tasks"

    def lookups(self, request, model_admin):
        return [
            (
                "supplier_payout_invoice_reconciles",
                "Supplier Price =/= Payout =/= Invoice Reconciles",
            ),
            (
                "customer_price_invoice_reconciles",
                "Customer Price =/= Invoice Reconciles",
            ),
            (
                "customer_price_paid_reconciles",
                "Customer Price =/= Paid Reconciles",
            ),
        ]

    def queryset(self, request, queryset):
        if self.value() == "supplier_payout_invoice_reconciles":
            order: Order
            for order in queryset:
                # Calculate the total Downstream has paid out to the supplier
                # for this order.
                payout_total = order.payouts.aggregate(Sum("amount"))["amount__sum"]

                # Calculate the total the supplier has invoiced Downstream for
                # this order.
                seller_invoice_total = (
                    order.seller_invoice_payable_line_items.aggregate(Sum("amount"))[
                        "amount__sum"
                    ]
                )

                # If the payout total and the seller invoice total do not match,
                # exclude the order from the queryset.
                if (
                    order.seller_price() != payout_total
                    and order.seller_price() != seller_invoice_total
                ):
                    queryset = queryset.exclude(id=order.id)

            # Return the filtered queryset.
            return queryset
        elif self.value() == "customer_price_invoice_reconciles":
            order: Order
            for order in queryset:
                # Get only the line items that have been invoiced.
                invoiced_order_line_items = order.order_line_items.filter(
                    stripe_invoice_line_item_id=True,
                )

                # Sum the customer price of the invoiced line items.
                customer_invoice_total = sum(
                    [
                        invoiced_order_line_item.customer_price()
                        for invoiced_order_line_item in invoiced_order_line_items
                    ]
                )

                # If the customer invoice total and the customer payment total
                # do not match, exclude the order from the queryset.
                if order.customer_price() != customer_invoice_total:
                    queryset = queryset.exclude(id=order.id)

            # Return the filtered queryset.
            return queryset
        elif self.value() == "customer_price_paid_reconciles":
            order: Order
            for order in queryset:
                # Get only the line items that have been paid.
                paid_order_line_items = order.order_line_items.filter(
                    paid=True,
                )

                # Sum the customer price of the paid line items.
                customer_paid_total = sum(
                    [
                        paid_order_line_item.customer_price()
                        for paid_order_line_item in paid_order_line_items
                    ]
                )

                # If the customer paid total and the customer payment total
                # do not match, exclude the order from the queryset.
                if order.customer_price() != customer_paid_total:
                    queryset = queryset.exclude(id=order.id)

            # Return the filtered queryset.
            return queryset
