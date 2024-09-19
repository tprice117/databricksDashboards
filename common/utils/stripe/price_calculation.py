from typing import Iterable, Union
import stripe
from django.conf import settings
import logging

stripe.api_key = settings.STRIPE_SECRET_KEY

logger = logging.getLogger(__name__)


ORDER_LINE_ITEM_MODEL = None


def get_order_line_item_model():
    """This imports the User model.
    This avoid the circular import issue."""
    global ORDER_LINE_ITEM_MODEL
    if ORDER_LINE_ITEM_MODEL is None:
        from api.models.order.order_line_item import (
            OrderLineItem as ORDER_LINE_ITEM_MODEL,
        )

    return ORDER_LINE_ITEM_MODEL


class PriceCalculation:

    @staticmethod
    def calculate_price_details(
        order,
        line_items: Iterable,
        delivery_fee: Union[int, float],
        update_line_items: bool = False,
    ) -> dict:
        """Get the price details for a Transaction/Order, primarily the taxes.
        This will calculate the taxes for the order and update the line items with the tax amount.

        Args:
            order (_type_): The Order/Transaction object.
            line_items (Iterable): An iterable of OrderLineItem objects.
            delivery_fee (Union[int, float]): The delivery fee. Pass in 0 if there is none.
            update_line_items (bool, optional): This will do a bulk update call to the database with the line items. Defaults to False.

        Returns:
            dict: _description_
        """
        try:
            country = "US"
            if order.order_group.user_address.country:
                country = order.order_group.user_address.country
                if country == "United States":
                    country = "US"

            # Stripe requires reference to be unique, so we need to combine the line items.
            combined_items = {}
            delivery_line_item = None
            for line_item in line_items:
                if line_item.order_line_item_type.code == "DELIVERY":
                    delivery_line_item = line_item
                else:
                    try:
                        combined_items[line_item.order_line_item_type.code][
                            "amount"
                        ] += int(line_item.customer_price() * 100)
                        combined_items[line_item.order_line_item_type.code][
                            "items"
                        ].append(line_item)
                    except KeyError:
                        combined_items[line_item.order_line_item_type.code] = {
                            "stripe_data": {
                                "amount": int(line_item.customer_price() * 100),
                                "tax_code": line_item.order_line_item_type.stripe_tax_code_id,
                                "reference": line_item.order_line_item_type.code,
                            },
                            "items": [line_item],
                        }
            stripe_items = [item["stripe_data"] for item in combined_items.values()]
            # https://docs.stripe.com/api/tax/calculations/object
            ret = stripe.tax.Calculation.create(
                currency="usd",
                customer_details={
                    "address": {
                        "line1": order.order_group.user_address.street,
                        "city": order.order_group.user_address.city,
                        "state": order.order_group.user_address.state,
                        "postal_code": order.order_group.user_address.postal_code,
                        "country": country,
                    },
                    "address_source": "shipping",
                },
                line_items=stripe_items,
                shipping_cost={"amount": int(delivery_fee * 100)},
                expand=["line_items"],
            )
            price_details = {
                "total": float(ret["amount_total"]) / 100,
                "taxes": float(ret["tax_amount_exclusive"]) / 100,
            }
            price_details["rate"] = float(0.0)
            # Get one-time fees: delivery, removal, fuels and fees, and taxes.
            price_details["one_time"] = {"estimated_taxes": float(0.00)}
            price_details["one_time"]["delivery"] = (
                float(ret["shipping_cost"]["amount"]) / 100
            )
            price_details["one_time"]["estimated_taxes"] += (
                float(ret["shipping_cost"]["amount_tax"]) / 100
            )
            for item in ret["line_items"]["data"]:
                combined_item = combined_items.get(item["reference"])
                if combined_item:
                    # Update the line items with the tax amount.
                    for line_item in combined_item["items"]:
                        line_type_total = combined_item["stripe_data"]["amount"] / 100
                        if line_item.tax is None:
                            if item["amount_tax"] == 0:
                                line_item.tax = 0
                            else:
                                line_amount = float(line_item.customer_price())
                                if len(combined_item["items"]) == 1:
                                    line_amount_rate = 1
                                else:
                                    # Get amount of the total is line_amount to determine how to split the tax.
                                    line_amount_rate = line_amount / line_type_total
                                line_item.tax = (
                                    line_amount_rate * item["amount_tax"] / 100
                                )

                # if item["reference"] == "DELIVERY":
                #     price_details["one_time"]["delivery"] = float(item["amount"]) / 100
                # elif item["reference"] == "SERVICE":
                #     price_details["one_time"]["service"] = float(item["amount"]) / 100
                # elif item["reference"] == "MATERIAL":
                #     price_details["one_time"]["material"] = float(item["amount"]) / 100
                # elif item["reference"] == "RENTAL":
                #     price_details["one_time"]["rental"] = float(item["amount"]) / 100
                if item["reference"] == "REMOVAL":
                    price_details["one_time"]["removal"] = float(item["amount"]) / 100
                    price_details["one_time"]["estimated_taxes"] += (
                        float(item["amount_tax"]) / 100
                    )
                elif item["reference"] == "FUEL_AND_ENV":
                    price_details["one_time"]["fuel_fees"] = float(item["amount"]) / 100

                    price_details["one_time"]["estimated_taxes"] += (
                        float(item["amount_tax"]) / 100
                    )
            if delivery_line_item and delivery_line_item.tax is None:
                delivery_line_item.tax = ret["shipping_cost"]["amount_tax"] / 100
            price_details["tax_breakdown"] = []
            for tax_details in ret["tax_breakdown"]:
                tax_rate = (
                    float(tax_details["tax_rate_details"]["percentage_decimal"]) / 100
                )
                if tax_rate > price_details["rate"]:
                    price_details["rate"] = tax_rate
                if tax_rate > 0:
                    price_details["tax_breakdown"].append(
                        {
                            "tax_type": tax_details["tax_rate_details"]["tax_type"],
                            "country": tax_details["tax_rate_details"]["country"],
                            "state": tax_details["tax_rate_details"]["state"],
                            "taxability_reason": tax_details["taxability_reason"],
                            "rate": tax_rate,
                            "amount": float(tax_details["amount"]) / 100,
                            "taxable_amount": float(tax_details["taxable_amount"])
                            / 100,
                        }
                    )

            if update_line_items:
                # Bulk update all line_items
                get_order_line_item_model().objects.bulk_update(line_items, ["tax"])

            return price_details
        except Exception as e:
            logger.error(
                f"PriceCalculation.calculate_price_details:Error: order: {order.id}-{e}"
            )
            return None
