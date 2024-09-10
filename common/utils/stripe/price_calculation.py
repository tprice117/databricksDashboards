import stripe
from decimal import Decimal
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY


class PriceCalculation:

    @staticmethod
    def calculate_price_details(order, line_items, delivery_fee):
        country = "US"
        if order.order_group.user_address.country:
            country = order.order_group.user_address.country
            if country == "United States":
                country = "US"

        stripe_items = []
        for key, line_item in line_items.items():
            if key != "DELIVERY":
                for item in line_item["items"]:
                    stripe_items.append(
                        {
                            "amount": int(item["customer_price"] * 100),
                            "tax_code": item["tax_code"],
                            "reference": key,
                        }
                    )
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
            "total": Decimal(ret["amount_total"]) / 100,
            "taxes": Decimal(ret["tax_amount_exclusive"]) / 100,
        }
        price_details["rate"] = Decimal(0.0)
        # Get one-time fees: delivery, removal, fuels and fees, and taxes.
        price_details["one_time"] = {"estimated_taxes": Decimal(0.00)}
        price_details["one_time"]["delivery"] = (
            Decimal(ret["shipping_cost"]["amount"]) / 100
        )
        price_details["one_time"]["estimated_taxes"] += (
            Decimal(ret["shipping_cost"]["amount_tax"]) / 100
        )
        for item in ret["line_items"]["data"]:
            # if item["reference"] == "DELIVERY":
            #     price_details["one_time"]["delivery"] = Decimal(item["amount"]) / 100
            # elif item["reference"] == "SERVICE":
            #     price_details["one_time"]["service"] = Decimal(item["amount"]) / 100
            # elif item["reference"] == "MATERIAL":
            #     price_details["one_time"]["material"] = Decimal(item["amount"]) / 100
            # elif item["reference"] == "RENTAL":
            #     price_details["one_time"]["rental"] = Decimal(item["amount"]) / 100
            if item["reference"] == "REMOVAL":
                price_details["one_time"]["removal"] = Decimal(item["amount"]) / 100
                price_details["one_time"]["estimated_taxes"] += (
                    Decimal(item["amount_tax"]) / 100
                )
            elif item["reference"] == "FUEL_AND_ENV":
                price_details["one_time"]["fuel_fees"] = Decimal(item["amount"]) / 100

                price_details["one_time"]["estimated_taxes"] += (
                    Decimal(item["amount_tax"]) / 100
                )
        price_details["tax_breakdown"] = []
        for tax_details in ret["tax_breakdown"]:
            tax_rate = (
                Decimal(tax_details["tax_rate_details"]["percentage_decimal"]) / 100
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
                        "amount": Decimal(tax_details["amount"]) / 100,
                        "taxable_amount": Decimal(tax_details["taxable_amount"]) / 100,
                    }
                )
        return price_details
