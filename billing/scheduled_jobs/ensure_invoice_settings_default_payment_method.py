from api.models.user.user_address import UserAddress
from common.utils.stripe.stripe_utils import StripeUtils
from payment_methods.models.payment_method import (
    PaymentMethod as DownstreamPaymentMethod,
)
import logging

logger = logging.getLogger(__name__)


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
        is_deleted = getattr(stripe_customer, "deleted", False)
        if is_deleted:
            try:
                # If the Stripe Customer is deleted, then update the UserAddress to
                # re-create the Stripe Customer.
                logger.warning(
                    f"Stripe Customer is deleted, re-create: [{user_address}][{user_address.id}][{user_address.stripe_customer_id}]"
                )
                user_address.stripe_customer_id = None
                user_address.save()
                # Get Stripe Customer.
                stripe_customer = StripeUtils.Customer.get(
                    user_address.stripe_customer_id,
                )
            except Exception as e:
                logger.error(
                    f"Stripe Customer is deleted, re-create:error: [{user_address}][{user_address.id}][{user_address.stripe_customer_id}]-[{e}]",
                    exc_info=e,
                )
                continue

        # Get the DefaultPaymentMethod for the Stripe Customer.
        default_payment_method = (
            StripeUtils.PaymentMethod.get(
                stripe_customer.invoice_settings.default_payment_method
            )
            if hasattr(stripe_customer, "invoice_settings")
            and stripe_customer.invoice_settings.default_payment_method
            else None
        )

        # If the DefaultPaymentMethod is set and is a Card, then ensure that it exists in our system and is active.
        if default_payment_method and default_payment_method.type == "card":
            # Get downstream payment method id from metadata.
            downstream_payment_method_id = default_payment_method["metadata"].get(
                "payment_method_id", None
            )
            if downstream_payment_method_id is not None:
                # Get the Downstream PaymentMethod object.
                downstream_payment_method = DownstreamPaymentMethod.objects.filter(
                    id=downstream_payment_method_id
                ).first()
            else:
                # The Downstream PaymentMethod ID is not found in the Stripe PaymentMethod metadata.
                downstream_payment_method = None

            if not downstream_payment_method:
                # This means that the Stripe PaymentMethod is not found in our system.
                default_payment_method = None
            elif not downstream_payment_method.active:
                # The Downstream PaymentMethod is inactive.
                default_payment_method = None

        # If the DefaultPaymentMethod is not set or is not a Card,
        # or the Downstream PaymentMethod is not found or inactive.
        if not default_payment_method or default_payment_method.type != "card":
            # Get a Downstream PaymentMethod for the UserAddress and update the Stripe default payment method.
            downstream_payment_method = user_address.get_payment_method()
            if downstream_payment_method:
                downstream_payment_method_id = str(downstream_payment_method.id)
                # Update the the Stripe default payment method
                stripe_payment_method = (
                    downstream_payment_method.set_stripe_default_payment_method(
                        user_address
                    )
                )
                if not stripe_payment_method:
                    # This payment method is not found in Stripe, though it is in our system.
                    # Reset DefaultPaymentMethod to None so that it can be re-set.
                    default_payment_method = None
                    logger.error(
                        f"ensure_invoice_settings_default_payment_method: Downstream PaymentMethod: [{downstream_payment_method_id}] not found in Stripe"
                    )
