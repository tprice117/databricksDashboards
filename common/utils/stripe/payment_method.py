import stripe
from stripe.error import InvalidRequestError
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY


class PaymentMethod:
    @staticmethod
    def list(customer_id: str):
        try:
            return stripe.Customer.list_payment_methods(
                customer_id,
                limit=100,
                type="card",
            )["data"]
        except InvalidRequestError as e:
            logger.error(
                f"stripe.PaymentMethod.list: [customer_id:{customer_id}]-[{e}]", exc_info=e
            )
            return []

    @staticmethod
    def attach(
        payment_method_id: str,
        customer_id: str,
    ):
        stripe.PaymentMethod.attach(
            payment_method_id,
            customer=customer_id,
        )
