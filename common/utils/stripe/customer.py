import stripe
from django.conf import settings

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
