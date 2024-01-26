import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY


class Transfer:
    @staticmethod
    def create(**kwargs):
        return stripe.Transfer.create(**kwargs)
