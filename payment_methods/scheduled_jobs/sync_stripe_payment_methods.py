from django.conf import settings

from payment_methods.models.payment_method import PaymentMethod


def sync_stripe_payment_methods():
    # Get all Payment Methods.
    payment_methods = PaymentMethod.objects.all()

    # Iterate over all Payment Methods and sync them with Stripe.
    payment_method: PaymentMethod
    for payment_method in payment_methods:
        payment_method.sync_stripe_payment_method()
