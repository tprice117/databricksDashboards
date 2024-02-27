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
            stripe_customer_payment_methods = StripeUtils.PaymentMethod.list(
                customer_id=user_address.stripe_customer_id,
            )
            print("stripe_customer_payment_methods: ", stripe_customer_payment_methods)

            # Check if the Payment Method is already synced with Stripe
            # for the UserAddress.
            print("------DONE")
            stripe_payment_method = next(
                (
                    method
                    for method in stripe_customer_payment_methods
                    if method.get("metadata", {}).get("token") == payment_method.token
                ),
                None,
            )
            # print("stripe_payment_method": stripe_payment_method)

            if stripe_payment_method:
                print("stripe_payment_method already exists")
            else:
                print("stripe_payment_method DOES NOT exist")

            # If the Payment Method is not already synced with Stripe
            # for the UserAddress, create it.
            if not stripe_payment_method:
                try:
                    response = _create_stripe_payment_method(
                        payment_method=payment_method
                    )

                    # Add the Payment Method to the UserAddress/Stripe Customer.
                    StripeUtils.PaymentMethod.attach(
                        payment_method_id=response["raw"],
                        customer_id=user_address.stripe_customer_id,
                    )
                    print("stripe_payment_method created")
                except Exception as e:
                    print(e)


def _create_stripe_payment_method(
    payment_method: PaymentMethod,
):
    return DSPaymentMethods.Reactors.invoke(
        reactor_id=settings.BASIS_THEORY_CREATE_PAYMENT_METHOD_REACTOR_ID,
        args={
            "token": payment_method.token,
            "payment_method_id": str(payment_method.id),
        },
    )
