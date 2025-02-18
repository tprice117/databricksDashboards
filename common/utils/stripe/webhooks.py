import json
import stripe
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from api.models import UserAddress
from billing.models import Invoice
import logging

stripe.api_key = settings.STRIPE_SECRET_KEY

logger = logging.getLogger(__name__)

# stripe.Event.type
ALLOWED_WEBHOOK_EVENTS = [
    "checkout.session.completed",
    "invoice.paid",
    "invoice.payment_failed",
    "invoice.payment_action_required",
    "invoice.upcoming",
    "invoice.marked_uncollectible",
    "invoice.payment_succeeded",
    # "payment_intent.succeeded",
    # "payment_intent.payment_failed",
    # "payment_intent.canceled",
    # "payment_method.attached",
]


def process_webhook_event(event: stripe.Event):
    #  // Skip processing if the event isn't one I'm tracking (list of all events below)
    if event.type not in ALLOWED_WEBHOOK_EVENTS:
        return

    if event.type == "checkout.session.completed":
        # https://docs.stripe.com/api/events/types#event_types-checkout.session.completed
        session = event["data"]["object"]
        logger.info(f"process_webhook_event: [{event.type}]: {session}")
        print("Checkout session completed!")
    elif event.type.startswith("invoice."):
        invoice = event.data.object  # contains a stripe.Invoice
        logger.info(f"process_webhook_event: [{event.type}]: {invoice}")
        user_address = UserAddress.objects.filter(
            stripe_customer_id=invoice["customer"],
        )

        if user_address.exists():
            user_address = user_address.first()
            Invoice.update_or_create_from_invoice(invoice, user_address)
    elif event.type == "payment_intent.succeeded":
        # https://docs.stripe.com/api/events/types#event_types-payment_intent.succeeded
        payment_intent = event.data.object  # contains a stripe.PaymentIntent
        logger.info(f"process_webhook_event: [{event.type}]: {payment_intent}")
        # Then define and call a method to handle the successful payment intent.
        # handle_payment_intent_succeeded(payment_intent)
    elif event.type == "payment_method.attached":
        # https://docs.stripe.com/api/events/types#event_types-payment_method.attached
        payment_method = event.data.object  # contains a stripe.PaymentMethod
        logger.info(f"process_webhook_event: [{event.type}]: {payment_method}")
        # Then define and call a method to handle the successful attachment of a PaymentMethod.
        # handle_payment_method_attached(payment_method)
    else:
        # Unexpected event type
        pass


@csrf_exempt
def stripe_webhook(request):
    # You can find your endpoint's secret in your webhook settings
    # endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
    # sig_header = request.META["HTTP_STRIPE_SIGNATURE"]

    payload = request.body
    event = None

    try:
        event = stripe.Event.construct_from(json.loads(payload), stripe.api_key)
    except ValueError:
        # Invalid payload
        return HttpResponse(status=400)

    # Handle the event
    # Handle the event
    error = process_webhook_event(event)
    if error:
        logger.error(f"Webhook error: {error}")

    return HttpResponse(status=200)
