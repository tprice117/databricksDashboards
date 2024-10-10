from typing import Iterable, Union, TypedDict
import logging
from django.core.exceptions import ValidationError
from django.utils import timezone
from api.models.order.order import Order
from api.models.user.user_address import UserAddress
from matching_engine.utils.prep_seller_product_seller_locations_for_response import (
    prep_seller_product_seller_locations_for_response,
)

from .models import CheckoutOrder

logger = logging.getLogger(__name__)


class PriceBreakdownPart(TypedDict):
    fuel_and_environmental: float
    tax: float
    total: float


class PriceBreakdown(TypedDict):
    service: Union[None, dict]
    rental: Union[None, dict]
    material: Union[None, dict]
    delivery: Union[None, dict]
    removal: Union[None, dict]
    fuel_and_environmental: Union[None, dict]
    total: float
    tax: float
    other: PriceBreakdownPart
    one_time: PriceBreakdownPart


class RentalBreakdownPart(TypedDict):
    base: float
    rpp_fee: Union[float, None]
    fuel_fees: float
    estimated_taxes: Union[float, None]
    subtotal: float
    total: float


class RentalBreakdown(TypedDict):
    day: Union[RentalBreakdownPart, None]
    week: Union[RentalBreakdownPart, None]
    month: Union[RentalBreakdownPart, None]


class CheckoutUtils:
    @staticmethod
    def checkout(
        user_address: UserAddress,
        orders: Iterable[Order],
        payment_method_id: Union[str, None],
    ) -> CheckoutOrder:
        try:
            # TODO: Until CheckoutOrder.payment_method is used when creating invoice just set as location default.
            if payment_method_id:
                user_address.default_payment_method_id = payment_method_id
                user_address.save()
            # Get the total price of all the orders.
            checkout_order = None
            order_id_lst = []
            customer_price = 0
            seller_price = 0
            estimated_taxes = 0
            total = 0
            for order in orders:
                order_id_lst.append(order.id)
                seller_price += order.seller_price()
                customer_price += order.customer_price()
                price_data = order.get_price()
                estimated_taxes += price_data["tax"]
                total += price_data["total"]
                if not checkout_order and order.checkout_order:
                    checkout_order: CheckoutOrder = order.checkout_order

            total = round(total, 2)  # Round to 2 decimal places.
            # If payment_method is None, then assume pay_later is True.
            if not payment_method_id:
                if (
                    user_address.user_group
                    and float(user_address.user_group.credit_limit_remaining) < total
                ):
                    raise ValidationError(
                        f"Company does not have enough credit to checkout [credit: {user_address.user_group.credit_limit_remaining} | total: {total:.2f}]."
                    )
            else:
                # TODO: Add in logic to create the invoice and check if the user has enough credit on their account in Stripe.
                pass

            # Submit all the orders.
            for order in orders:
                order.submit_order(override_approval_policy=True)

            if checkout_order:
                if payment_method_id:
                    checkout_order.payment_method = user_address.default_payment_method
                else:
                    checkout_order.pay_later = True
                checkout_order.customer_price = customer_price
                checkout_order.seller_price = seller_price
                checkout_order.estimated_taxes = estimated_taxes
                checkout_order.take_rate = order.order_group.take_rate
                checkout_order.save()
            else:
                checkout_order = CheckoutOrder(
                    user_address=user_address,
                    customer_price=customer_price,
                    seller_price=seller_price,
                    estimated_taxes=estimated_taxes,
                    quote="",
                )
                if payment_method_id:
                    checkout_order.payment_method = user_address.default_payment_method
                else:
                    checkout_order.pay_later = True
                checkout_order.save()
                # Update transactions/orders to point to the checkout order
                Order.objects.filter(id__in=order_id_lst).update(
                    checkout_order=checkout_order
                )
            return checkout_order
        except Exception as e:
            # Catch and log the exception and then re-raise it.
            logger.exception(
                f"CheckoutUtils.checkout: [{user_address}]-[{orders}]-[{payment_method_id}]-[{e}]"
            )
            raise e


class QuoteUtils:

    @staticmethod
    def get_rental_breakdown(
        seller_product_seller_location,
        main_product,
        fuel_fee_rate,
        estimated_tax_rate: float = None,
        add_rpp_fee=True,
    ) -> Union[RentalBreakdown, None]:
        """Creates breakdown for rental multi-step products with fuel fees, RPP, and estimated taxes (if available).

        Args:
            seller_product_seller_location (SellerProductSellerLocation): The SellerProductSellerLocation object.
            main_product (MainProduct): The MainProduct object.
            fuel_fee_rate (float | decimal): Fuel fee rate.
            estimated_tax_rate (float, optional): Estimated tax rate. Adds tax if set. Defaults to None.
            add_rpp_fee (bool, optional): Adds RPP if set to True. Defaults to True.

        Returns:
            Union[RentalBreakdown, None]: _description_
        """
        # Update the SellerProductSellerLocation to default to the take rate.
        seller_product_seller_location_resp = (
            prep_seller_product_seller_locations_for_response(
                main_product=main_product,
                seller_product_seller_locations=[seller_product_seller_location],
            )[0]
        )
        if seller_product_seller_location_resp["rental_multi_step"]:
            rental_breakdown: RentalBreakdown = {
                "day": None,
                "week": None,
                "month": None,
            }
            if (
                seller_product_seller_location_resp["rental_multi_step"]["day"]
                is not None
            ):
                rental_breakdown["day"] = {
                    "base": float(
                        seller_product_seller_location_resp["rental_multi_step"]["day"]
                    ),
                    "rpp_fee": None,
                    "fuel_fees": 0,
                    "estimated_taxes": None,
                    "subtotal": 0,
                    "total": 0,
                }
            if (
                seller_product_seller_location_resp["rental_multi_step"]["week"]
                is not None
            ):
                rental_breakdown["week"] = {
                    "base": float(
                        seller_product_seller_location_resp["rental_multi_step"]["week"]
                    ),
                    "rpp_fee": None,
                    "fuel_fees": 0,
                    "estimated_taxes": None,
                    "subtotal": 0,
                    "total": 0,
                }
            if (
                seller_product_seller_location_resp["rental_multi_step"]["month"]
                is not None
            ):
                rental_breakdown["month"] = {
                    "base": float(
                        seller_product_seller_location_resp["rental_multi_step"][
                            "month"
                        ]
                    ),
                    "rpp_fee": None,
                    "fuel_fees": 0,
                    "estimated_taxes": None,
                    "subtotal": 0,
                    "total": 0,
                }
            # Add total, fuel fees, and estimated taxes to the rental breakdown.
            for key in rental_breakdown:
                if rental_breakdown[key] is None:
                    continue
                rental_breakdown[key]["fuel_fees"] = round(
                    rental_breakdown[key]["base"] * float(fuel_fee_rate / 100),
                    2,
                )
                rental_breakdown[key]["subtotal"] += rental_breakdown[key]["base"]
                rental_breakdown[key]["subtotal"] += rental_breakdown[key]["fuel_fees"]

                if add_rpp_fee:
                    # Add a 15% Rental Protection Plan fee if the user does not have their own COI.
                    rental_breakdown[key]["rpp_fee"] = round(
                        rental_breakdown[key]["base"] * float(0.15), 2
                    )
                    rental_breakdown[key]["subtotal"] += rental_breakdown[key][
                        "rpp_fee"
                    ]

                rental_breakdown[key]["total"] = rental_breakdown[key]["subtotal"]

                if estimated_tax_rate is not None:
                    rental_breakdown[key]["estimated_taxes"] = round(
                        rental_breakdown[key]["base"] * float(estimated_tax_rate / 100),
                        2,
                    )
                    rental_breakdown[key]["total"] += rental_breakdown[key][
                        "estimated_taxes"
                    ]

            return rental_breakdown
        return None

    @staticmethod
    def get_price_breakdown(
        price_data, seller_product_seller_location, main_product, user_group=None
    ) -> PriceBreakdown:
        """Accepts a price_data dictionary and returns a price breakdown dictionary.

        Args:
            price_data (PriceBreakdown): The price_data dictionary.
            seller_product_seller_location (SellerProductSellerLocation): The SellerProductSellerLocation object.
            main_product (MainProduct): The MainProduct object.
            user_group (UserGroup, optional): The UserGroup object used to check if RRP is needed. Defaults to None.

        Returns: PriceBreakdown"""

        price_breakdown: PriceBreakdown = {
            "service": None,
            "rental": None,
            "material": None,
            "delivery": None,
            "removal": None,
            "fuel_and_environmental": None,
            "total": 0,
            "tax": 0,
            "estimated_tax_rate": 0,
            "pre_tax_subtotal": 0,
            "fuel_and_environmental_rate": 0,
            "other": {"fuel_and_environmental": 0, "tax": 0, "total": 0},
            "one_time": {"fuel_and_environmental": 0, "tax": 0, "total": 0},
        }
        # load the price data into the item
        price_breakdown["pre_tax_subtotal"] = price_data["total"] - price_data["tax"]
        # load the price data into the item
        for key in price_data:
            price_breakdown[key] = price_data[key]

        # All calculations below should happen when displaying the data
        if price_breakdown["rental"]:
            if price_breakdown["rental"]["tax"] > 0:
                # Get estimated tax rate by checking delivery fee tax rate
                price_breakdown["estimated_tax_rate"] = round(
                    (
                        price_breakdown["rental"]["tax"]
                        / price_breakdown["rental"]["total"]
                    )
                    * 100,
                    4,
                )

        # Calculate the one-time (delivery + removal) fuel fees, estimated taxes, and total
        if price_breakdown["delivery"]:
            price_breakdown["one_time"]["total"] += price_breakdown["delivery"]["total"]
            price_breakdown["one_time"]["tax"] += price_breakdown["delivery"]["tax"]
            if (
                price_breakdown["estimated_tax_rate"] == 0
                and price_breakdown["delivery"]["tax"] > 0
            ):
                # Get estimated tax rate by checking delivery fee tax rate
                price_breakdown["estimated_tax_rate"] = round(
                    (
                        price_breakdown["delivery"]["tax"]
                        / price_breakdown["delivery"]["total"]
                    )
                    * 100,
                    4,
                )
        if price_breakdown["removal"]:
            price_breakdown["one_time"]["total"] += price_breakdown["removal"]["total"]
            price_breakdown["one_time"]["tax"] += price_breakdown["removal"]["tax"]

        if price_breakdown["fuel_and_environmental"]:
            # Calculate the one-time fuel fees and estimated taxes
            fuel_fees_subtotal = (
                price_breakdown["fuel_and_environmental"]["total"]
                - price_breakdown["fuel_and_environmental"]["tax"]
            )
            # Get percentage that one_time total is of total minus fuel fees
            total_minus_fuel = price_breakdown["pre_tax_subtotal"] - fuel_fees_subtotal
            one_time_total_percentage = round(
                price_breakdown["one_time"]["total"] / total_minus_fuel, 6
            )
            price_breakdown["one_time"]["fuel_and_environmental"] = (
                fuel_fees_subtotal * one_time_total_percentage
            )
            # Get fuel fees for the rest of the total (not one-time)
            price_breakdown["other"]["fuel_and_environmental"] = abs(
                fuel_fees_subtotal
                - price_breakdown["one_time"]["fuel_and_environmental"]
            )
            fuel_fees_tax = (
                price_breakdown["fuel_and_environmental"]["tax"]
                * one_time_total_percentage
            )
            # rest_of_total_tax = abs(
            #     item["fuel_and_environmental"]["tax"] - fuel_fees_tax
            # )
            price_breakdown["one_time"]["tax"] += fuel_fees_tax

            # Calculate the fuel fees rate (display only)
            fuel_rate = price_breakdown["fuel_and_environmental"]["total"] / (
                price_breakdown["total"]
                - price_breakdown["fuel_and_environmental"]["total"]
            )
            # From self.order_group.seller_product_seller_location.fuel_environmental_markup
            price_breakdown["fuel_and_environmental_rate"] = round(fuel_rate * 100, 4)

        if price_breakdown["estimated_tax_rate"] > 0:
            # Get taxes for the Service section
            price_breakdown["other"]["tax"] = abs(
                price_breakdown["tax"] - price_breakdown["one_time"]["tax"]
            )

        # Add fuel fees and estimated taxes to the one-time total
        price_breakdown["one_time"]["total"] += (
            price_breakdown["one_time"]["fuel_and_environmental"]
            + price_breakdown["one_time"]["tax"]
        )

        # Add fuel fees and estimated taxes to the other total
        price_breakdown["other"]["total"] += (
            price_breakdown["other"]["fuel_and_environmental"]
            + price_breakdown["other"]["tax"]
        )

        # Calculate Service total
        if price_breakdown["service"]:
            price_breakdown["other"]["total"] += price_breakdown["service"]["total"]
        if price_breakdown["material"]:
            price_breakdown["other"]["total"] += price_breakdown["material"]["total"]
        if price_breakdown["rental"]:
            price_breakdown["other"]["total"] += price_breakdown["rental"]["total"]

        # Get rental breakdown for multi-step rentals
        add_rpp_fee = False
        if user_group is None:
            add_rpp_fee = True
        elif not user_group.owned_and_rented_equiptment_coi:
            add_rpp_fee = True
        price_breakdown["rental_breakdown"] = QuoteUtils.get_rental_breakdown(
            seller_product_seller_location,
            main_product,
            price_breakdown["fuel_and_environmental_rate"],
            estimated_tax_rate=price_breakdown["estimated_tax_rate"],
            add_rpp_fee=add_rpp_fee,
        )
        return price_breakdown

    @staticmethod
    def create_quote(order_id_lst, email_lst, quote_sent=True) -> CheckoutOrder:
        # Put in checkout app.
        # OR: Or separate app called quote.
        # Put the stripe call into common stripe
        orders = Order.objects.filter(id__in=order_id_lst)
        orders = orders.prefetch_related("order_line_items")
        one_step = []
        two_step = []
        multi_step = []
        total = float(0.00)
        seller_total = float(0.00)
        total_taxes = float(0.00)
        project_id = "N/A"

        for order in orders:
            seller_total += float(order.seller_price())
            item = {
                "product": {
                    "name": order.order_group.seller_product_seller_location.seller_product.product.main_product.name,
                    "image": order.order_group.seller_product_seller_location.seller_product.product.main_product.main_product_category.icon.url,
                },
                "start_date": order.start_date.strftime("%m/%d/%Y"),
                "tonnage_quantity": order.order_group.tonnage_quantity,
                "addons": [],
                "subtotal": float(0.00),
                "fuel_fees": float(0.00),
                # This is the total tax
                "tax": float(0.00),
                # This is the tax minus the one time tax
                "estimated_taxes": float(0.00),
                "estimated_tax_rate": float(0.00),
                "pre_tax_subtotal": float(order.customer_price()),
                "service_total": float(0.00),
                # This is the total for this Transaction/Order
                "total": float(0.00),
                "fuel_and_environmental_rate": float(0.00),
                "one_time": {
                    "delivery": float(0.00),
                    "removal": float(0.00),
                    "fuel_fees": float(0.00),
                    "estimated_taxes": float(0.00),
                    # A sum of all the one-time fees
                    "total": float(0.00),
                },
                "schedule_window": order.schedule_window,
            }
            if not item["schedule_window"]:
                if item.order.order_group.time_slot:
                    item["schedule_window"] = (
                        f"{order.order_group.time_slot.name} ({order.order_group.time_slot.start}-{order.order_group.time_slot.end})"
                    )
                else:
                    item["schedule_window"] = "Anytime (7am-4pm)"
            addons = (
                order.order_group.seller_product_seller_location.seller_product.product.product_add_on_choices.all()
            )
            for addon in addons:
                item["addons"].append(
                    {
                        "key": addon.add_on_choice.add_on.name,
                        "val": addon.add_on_choice.name,
                    }
                )
            price_data = order.get_price()
            item["pre_tax_subtotal"] = price_data["total"] - price_data["tax"]
            # load the price data into the item
            for key in price_data:
                item[key] = price_data[key]

            total_taxes += item["tax"]

            # All calculations below should happen when displaying the data
            if item["rental"]:
                if item["rental"]["tax"] > 0:
                    # Get estimated tax rate by checking delivery fee tax rate
                    item["estimated_tax_rate"] = round(
                        (item["rental"]["tax"] / item["rental"]["total"]) * 100,
                        4,
                    )

            # Calculate the one-time fuel fees and estimated taxes
            if item["delivery"]:
                item["one_time"]["delivery"] = (
                    item["delivery"]["total"] - item["delivery"]["tax"]
                )
                item["one_time"]["estimated_taxes"] += item["delivery"]["tax"]
                if item["estimated_tax_rate"] == 0 and item["delivery"]["tax"] > 0:
                    # Get estimated tax rate by checking delivery fee tax rate
                    item["estimated_tax_rate"] = round(
                        (item["delivery"]["tax"] / item["one_time"]["delivery"]) * 100,
                        4,
                    )
            if item["removal"]:
                item["one_time"]["removal"] = (
                    item["removal"]["total"] - item["removal"]["tax"]
                )
                item["one_time"]["estimated_taxes"] += item["removal"]["tax"]

            # Calculate the one-time total (delivery + removal)
            item["one_time"]["total"] = (
                item["one_time"]["delivery"] + item["one_time"]["removal"]
            )

            if item["fuel_and_environmental"]:
                # Calculate the one-time fuel fees and estimated taxes
                fuel_fees_subtotal = (
                    item["fuel_and_environmental"]["total"]
                    - item["fuel_and_environmental"]["tax"]
                )
                # Get percentage that one_time total is of total minus fuel fees
                total_minus_fuel = item["pre_tax_subtotal"] - fuel_fees_subtotal
                one_time_total_percentage = round(
                    item["one_time"]["total"] / total_minus_fuel, 6
                )
                item["one_time"]["fuel_fees"] = (
                    fuel_fees_subtotal * one_time_total_percentage
                )
                # Get fuel fees for the rest of the total (not one-time)
                item["fuel_fees"] = abs(
                    fuel_fees_subtotal - item["one_time"]["fuel_fees"]
                )
                fuel_fees_tax = (
                    item["fuel_and_environmental"]["tax"] * one_time_total_percentage
                )
                # rest_of_total_tax = abs(
                #     item["fuel_and_environmental"]["tax"] - fuel_fees_tax
                # )
                item["one_time"]["estimated_taxes"] += fuel_fees_tax

                # Calculate the fuel fees rate (display only)
                fuel_rate = item["fuel_and_environmental"]["total"] / (
                    item["total"] - item["fuel_and_environmental"]["total"]
                )
                # From self.order_group.seller_product_seller_location.fuel_environmental_markup
                item["fuel_and_environmental_rate"] = round(fuel_rate * 100, 4)

            if item["estimated_tax_rate"] > 0:
                # Get taxes for the Service section
                item["estimated_taxes"] = abs(
                    item["tax"] - item["one_time"]["estimated_taxes"]
                )

            # Add fuel fees and estimated taxes to the one-time total
            item["one_time"]["total"] += (
                item["one_time"]["fuel_fees"] + item["one_time"]["estimated_taxes"]
            )

            # This is Subtotal
            if item["service"]:
                item["subtotal"] += item["service"]["total"] - item["service"]["tax"]
            if item["material"]:
                item["subtotal"] += item["material"]["total"] - item["material"]["tax"]
            if item["rental"]:
                item["subtotal"] += item["rental"]["total"] - item["rental"]["tax"]

            # This is Total (Per Service)
            item["service_total"] = (
                item["subtotal"] + item["fuel_fees"] + item["estimated_taxes"]
            )

            if order.order_group.user_address.project_id:
                project_id = order.order_group.user_address.project_id
            if (
                order.order_type == Order.Type.DELIVERY
                and order.order_group.seller_product_seller_location.seller_product.product.main_product.has_rental_multi_step
            ):
                total += item["one_time"]["total"]
            else:
                total += item["total"]
            if (
                order.order_group.seller_product_seller_location.seller_product.product.main_product.has_rental
            ):
                two_step.append(item)
            elif (
                order.order_group.seller_product_seller_location.seller_product.product.main_product.has_rental_one_step
            ):
                one_step.append(item)
            elif (
                order.order_group.seller_product_seller_location.seller_product.product.main_product.has_rental_multi_step
            ):
                item["rental_breakdown"] = {
                    "day": {
                        "base": float(
                            order.order_group.seller_product_seller_location.rental_multi_step.day
                        ),
                        "rpp_fee": float(0.00),
                    },
                    "week": {
                        "base": float(
                            order.order_group.seller_product_seller_location.rental_multi_step.week
                        ),
                        "rpp_fee": float(0.00),
                    },
                    "month": {
                        "base": float(
                            order.order_group.seller_product_seller_location.rental_multi_step.month
                        ),
                        "rpp_fee": float(0.00),
                    },
                }
                # Add total, fuel fees, and estimated taxes to the rental breakdown.
                for key in item["rental_breakdown"]:
                    item["rental_breakdown"][key]["fuel_fees"] = round(
                        item["rental_breakdown"][key]["base"]
                        * float(item["fuel_and_environmental_rate"] / 100),
                        2,
                    )
                    item["rental_breakdown"][key]["estimated_taxes"] = round(
                        item["rental_breakdown"][key]["base"]
                        * float(item["estimated_tax_rate"] / 100),
                        2,
                    )
                    add_rpp_fee = False
                    if order.order_group.user.user_group is None:
                        add_rpp_fee = True
                    elif (
                        not order.order_group.user.user_group.owned_and_rented_equiptment_coi
                    ):
                        add_rpp_fee = True
                    if add_rpp_fee:
                        # Add a 15% Rental Protection Plan fee if the user does not have their own COI.
                        item["rental_breakdown"][key]["rpp_fee"] = round(
                            item["rental_breakdown"][key]["base"] * float(0.15), 2
                        )
                    item["rental_breakdown"][key]["subtotal"] = round(
                        item["rental_breakdown"][key]["base"]
                        + item["rental_breakdown"][key]["fuel_fees"]
                        + item["rental_breakdown"][key]["rpp_fee"],
                        2,
                    )
                    item["rental_breakdown"][key]["total"] = round(
                        item["rental_breakdown"][key]["base"]
                        + item["rental_breakdown"][key]["fuel_fees"]
                        + item["rental_breakdown"][key]["estimated_taxes"]
                        + item["rental_breakdown"][key]["rpp_fee"],
                        2,
                    )

                multi_step.append(item)

        subject = (
            "Downstream | Quote | " + order.order_group.user_address.formatted_address()
        )
        quote_expiration = timezone.now() + timezone.timedelta(days=15)
        if order.order_group.user.user_group:
            company_name = order.order_group.user.user_group.name
        else:
            company_name = order.order_group.user.full_name
        billing_address = "N/A"
        billing_email = order.order_group.user.email
        if order.order_group.user.user_group:
            if hasattr(order.order_group.user.user_group, "billing"):
                billing_address = (
                    order.order_group.user.user_group.billing.formatted_address
                )
                billing_email = order.order_group.user.user_group.billing.email

        quote_data = {
            "quote_expiration": quote_expiration.strftime("%B %d, %Y"),
            "quote_id": "N/A",
            "project_id": project_id,
            "full_name": order.order_group.user.full_name,
            "company_name": company_name,
            "delivery_address": order.order_group.user_address.formatted_address(),
            "billing_address": billing_address,
            "billing_email": billing_email,
            "one_step": one_step,
            "two_step": two_step,
            "multi_step": multi_step,
            "total": f"{total:,.2f}",
            "estimated_taxes": total_taxes,
        }
        if order.checkout_order:
            checkout_order = order.checkout_order
            quote_data["quote_id"] = checkout_order.code
            if checkout_order.quote_expiration:
                quote_data["quote_expiration"] = (
                    checkout_order.quote_expiration.strftime("%B %d, %Y")
                )
            # Update the checkout order
            order.checkout_order.payment_method = (
                order.order_group.user_address.default_payment_method
            )
            order.checkout_order.quote = quote_data
            order.checkout_order.customer_price = total
            order.checkout_order.seller_price = seller_total
            if quote_sent:
                order.checkout_order.quote_expiration = quote_expiration
            order.checkout_order.save()
        else:
            # Create a checkout order
            checkout_order = CheckoutOrder(
                user_address=order.order_group.user_address,
                payment_method=order.order_group.user_address.default_payment_method,
                quote=quote_data,
                customer_price=total,
                seller_price=seller_total,
                subject=subject,
            )
            if email_lst:
                checkout_order.to_emails = ",".join(email_lst)
            if quote_sent:
                checkout_order.quote_expiration = quote_expiration
            checkout_order.save()
            quote_data["quote_id"] = checkout_order.code

        # Update events to point to the checkout order
        Order.objects.filter(id__in=order_id_lst).update(checkout_order=checkout_order)

        return checkout_order
