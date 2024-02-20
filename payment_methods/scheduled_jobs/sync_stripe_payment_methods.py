from django.conf import settings

from api.models import UserAddress
from common.utils.stripe.stripe_utils import StripeUtils
from payment_methods.models.payment_method import PaymentMethod
from payment_methods.utils.payment_methods import DSPaymentMethods


def sync_stripe_payment_methods():
    print("got here")
    # Get all Payment Methods.
    payment_methods = PaymentMethod.objects.all()

    # Iterate over all Payment Methods and sync them with Stripe.
    for payment_method in payment_methods:
        # For the Payment Method UserGroup, find any UserAddresses
        # (Stripe Customers) that don't have the Payment Method
        # (see the payment_method.metadata["token"]).
        user_addresses = payment_method.user_group.user_addresses.all()

        # Iterate over all UserAddresses and sync them with Stripe.
        user_address: UserAddress
        for user_address in user_addresses:
            # Get all Payment Methods for the UserAddress.
            stripe_payment_methods = StripeUtils.PaymentMethod.list(
                customer_id=user_address.stripe_customer_id,
            )

            # Check if the Payment Method is already synced with Stripe
            # for the UserAddress.
            stripe_payment_method = next(
                (
                    stripe_payment_method
                    for stripe_payment_method in stripe_payment_methods
                    if "token" in stripe_payment_method.metadata
                    and stripe_payment_method.metadata["token"]
                    == payment_method.metadata["token"]
                ),
                None,
            )

            # If the Payment Method is not already synced with Stripe
            # for the UserAddress, create it.
            if not stripe_payment_method:
                try:
                    response = _create_stripe_payment_method(
                        payment_method=payment_method
                    )
                    print(response)
                    print("---------------YES----------------")
                except Exception as e:
                    print(e)
                    print("---------------NO----------------")


def _create_stripe_payment_method(
    payment_method: PaymentMethod,
):
    return DSPaymentMethods.Reactors.invoke(
        reactor_id=settings.BASIS_THEORY_CREATE_PAYMENT_METHOD_REACTOR_ID,
        args={
            "token": "1fe0d69a-3244-47d8-8463-d1171b134753",  # payment_method.token,
        },
    )
