from decimal import Decimal
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
        total = Decimal(0.00)
        seller_total = Decimal(0.00)
        total_taxes = Decimal(0.00)

        for order in orders:
            seller_total += order.seller_price()
            item = order.get_order_with_tax()
            total_taxes += item["taxes"]
            if (
                order.order_type == Order.Type.DELIVERY
                and order.order_group.seller_product_seller_location.seller_product.product.main_product.has_rental_multi_step
            ):
                total += item["one_time"]["total"]
            else:
                total += item["total"] + item["one_time"]["total"]
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
                        "base": order.order_group.seller_product_seller_location.rental_multi_step.day,
                        "rpp_fee": Decimal(0.00),
                    },
                    "week": {
                        "base": order.order_group.seller_product_seller_location.rental_multi_step.week,
                        "rpp_fee": Decimal(0.00),
                    },
                    "month": {
                        "base": order.order_group.seller_product_seller_location.rental_multi_step.month,
                        "rpp_fee": Decimal(0.00),
                    },
                }
                # Add total, fuel fees, and estimated taxes to the rental breakdown.
                for key in item["rental_breakdown"]:
                    item["rental_breakdown"][key]["fuel_fees"] = round(
                        item["rental_breakdown"][key]["base"]
                        * Decimal(item["fuel_fees_rate"] / 100),
                        2,
                    )
                    item["rental_breakdown"][key]["estimated_taxes"] = round(
                        item["rental_breakdown"][key]["base"]
                        * Decimal(item["estimated_tax_rate"] / 100),
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
                            item["rental_breakdown"][key]["base"] * Decimal(0.15), 2
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
        quote_expiration = timezone.now() + timezone.timedelta(days=14)
        if order.order_group.user.user_group:
            company_name = order.order_group.user.user_group.name
        else:
            company_name = order.order_group.user.full_name
        quote_data = {
            "quote_expiration": quote_expiration.strftime("%B %d, %Y"),
            "quote_id": "N/A",
            "full_name": order.order_group.user.full_name,
            "company_name": company_name,
            "delivery_address": order.order_group.user_address.formatted_address(),
            "billing_address": order.order_group.seller_product_seller_location.seller_location.formatted_address,
            "billing_email": order.order_group.seller_product_seller_location.seller_location.order_email,
            "one_step": one_step,
            "two_step": two_step,
            "multi_step": multi_step,
            "total": f"{total:,.2f}",
            "estimated_taxes": total_taxes,
            "contact": {
                "full_name": order.created_by.full_name,
                "email": order.created_by.email,
                "phone": order.created_by.phone,  # (720) 490-1823
            },
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
