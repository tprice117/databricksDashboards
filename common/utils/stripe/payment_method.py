import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY


class PaymentMethod:
    @staticmethod
    def list(customer_id: str):
        return stripe.Customer.list_payment_methods(
            customer_id,
            limit=100,
            type="card",
        )["data"]

    @staticmethod
    def attach(
        payment_method_id: str,
        customer_id: str,
    ):
        stripe.PaymentMethod.attach(
            payment_method_id,
            customer=customer_id,
        )
