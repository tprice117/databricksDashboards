from django.urls import path

from common.utils.stripe.webhooks import stripe_webhook
from common.utils.customerio import customerio_webhook

urlpatterns = [
    path("webhook/stripe/", customerio_webhook),
    path("webhook/customerio/", stripe_webhook),
]
