from django.utils import timezone
from api.models.order.order import Order

from .models import CheckoutOrder


class QuoteUtils:
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
            # load the price data into the item
            for key in price_data.data:
                item[key] = price_data.data[key]
            total_taxes += item["tax"]

            # TODO: All calculations below should happen when displaying the data
            if item["rental"]:
                if item["rental"]["tax"] > 0:
                    # Get estimated tax rate by checking delivery fee tax rate
                    item["estimated_tax_rate"] = round(
                        (item["rental"]["tax"] / item["rental"]["total"]) * 100,
                        4,
                    )

            # Calculate the one-time fuel fees and estimated taxes
            if item["delivery"]:
                item["one_time"]["delivery"] = item["delivery"]["total"]
                item["one_time"]["estimated_taxes"] += item["delivery"]["tax"]
                if item["estimated_tax_rate"] == 0 and item["delivery"]["tax"] > 0:
                    # Get estimated tax rate by checking delivery fee tax rate
                    item["estimated_tax_rate"] = round(
                        (item["delivery"]["tax"] / item["one_time"]["delivery"]) * 100,
                        4,
                    )
            if item["removal"]:
                item["one_time"]["removal"] = item["removal"]["total"]
                item["one_time"]["estimated_taxes"] += item["removal"]["tax"]

            # Calculate the one-time total (delivery + removal)
            item["one_time"]["total"] = (
                item["one_time"]["delivery"] + item["one_time"]["removal"]
            )

            if item["fuel_and_environmental"]:
                # What percentage is one_time total of the total?
                one_time_total_percentage = (
                    item["one_time"]["total"] / item["pre_tax_subtotal"]
                )
                # Calculate the one-time fuel fees and estimated taxes
                item["one_time"]["fuel_fees"] = (
                    item["fuel_and_environmental"]["total"] * one_time_total_percentage
                )
                # Calculate the fuel fees rate
                fuel_rate = item["fuel_and_environmental"]["total"] / (
                    item["total"] - item["fuel_and_environmental"]["total"]
                )
                # From self.order_group.seller_product_seller_location.fuel_environmental_markup
                item["fuel_and_environmental_rate"] = round(fuel_rate * 100, 4)

            if item["estimated_tax_rate"] > 0:
                item["estimated_taxes"] = abs(
                    item["tax"] - item["one_time"]["estimated_taxes"]
                )
            else:
                item["one_time"]["estimated_taxes"] = float(0.00)

            # Add fuel fees and estimated taxes to the one-time total
            item["one_time"]["total"] += (
                item["one_time"]["fuel_fees"] + item["one_time"]["estimated_taxes"]
            )

            # Get fuel fees for the rest of the total (not one-time)
            item["fuel_fees"] = abs(item["one_time"]["fuel_fees"] - item["fuel_fees"])

            # This is Subtotal  # - item["estimated_taxes"],
            item["subtotal"] = (
                item["total"]
                - item["fuel_fees"]
                - item["one_time"]["total"]
                + item["one_time"]["estimated_taxes"]
            )

            # This is Total (Per Service)
            item["service_total"] = item["subtotal"] + item["estimated_taxes"]

            if order.order_group.user_address.project_id:
                project_id = order.order_group.user_address.project_id
            if (
                order.order_type == Order.Type.DELIVERY
                and order.order_group.seller_product_seller_location.seller_product.product.main_product.has_rental_multi_step
            ):
                total += item["one_time"]["total"]
            else:
                total += item["service_total"] + item["one_time"]["total"]
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
