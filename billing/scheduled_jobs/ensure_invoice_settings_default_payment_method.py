from api.models.user.user_address import UserAddress
from common.utils.stripe.stripe_utils import StripeUtils


def ensure_invoice_settings_default_payment_method():
    """
    Ensure that the Customer.InvoiceSettings.DefaultPaymentMethod is set to a Card
    for all Stripe Customers that have a Card on file.
    """

    # Get all UserAddresses (aka Stripe Customers).
    user_addresses = UserAddress.objects.all()

    # Iterate over all UserAddresses and ensure that the DefaultPaymentMethod is set.
    user_address: UserAddress
    for user_address in user_addresses:
        # Get Stripe Customer.
        stripe_customer = StripeUtils.Customer.get(
            user_address.stripe_customer_id,
        )

        # Get the DefaultPaymentMethod for the Stripe Customer.
        default_payment_method = (
            StripeUtils.PaymentMethod.get(
                stripe_customer.invoice_settings.default_payment_method
            )
            if hasattr(stripe_customer, "invoice_settings")
            and stripe_customer.invoice_settings.default_payment_method
            else None
        )

        # If the DefaultPaymentMethod is not set or is not a Card, then fetch
        # all Payment Methods and set the DefaultPaymentMethod to a Card, if
        # one exists.
        if not default_payment_method or default_payment_method.type != "card":
            # Get all Payment Methods for the Stripe Customer (card type only).
            payment_methods = StripeUtils.PaymentMethod.list(
                customer_id=user_address.stripe_customer_id,
            )

            # Iterate over all Payment Methods and ensure that the DefaultPaymentMethod is set.
            for payment_method in payment_methods:
                if payment_method["type"] == "card":
                    StripeUtils.Customer.update(
                        user_address.stripe_customer_id,
                        invoice_settings={
                            "default_payment_method": payment_method["id"],
                        },
                    )
                    break
