import stripe
from django.conf import settings

from .payment_method import PaymentMethod as PaymentMethodUtils

stripe.api_key = settings.STRIPE_SECRET_KEY


class Customer:
    @staticmethod
    def create():
        return stripe.Customer.create()

    @staticmethod
    def get(id: str):
        return stripe.Customer.retrieve(id)

    @staticmethod
    def update(id: str, **kwargs):
        return stripe.Customer.modify(id, **kwargs)

    @staticmethod
    def ensure_default_payment_method(customer_id: str, payment_method_id: str = None):
        """
        Ensure that the DefaultPaymentMethod is set for the Stripe Customer.
        """
        if payment_method_id:
            return stripe.Customer.modify(
                customer_id,
                invoice_settings={
                    "default_payment_method": payment_method_id,
                },
            )
        else:
            # Get all Payment Methods for the Stripe Customer (card type only).
            payment_methods = PaymentMethodUtils.list(customer_id=customer_id)
            # Iterate over all Payment Methods and ensure that the DefaultPaymentMethod is set.
            customer = None
            for payment_method in payment_methods:
                if payment_method["type"] == "card":
                    customer = Customer.update(
                        customer_id,
                        invoice_settings={
                            "default_payment_method": payment_method["id"],
                        },
                    )
                    break
        return customer
