from typing import List
import logging
import stripe
from django.conf import settings
from .customer import Customer
from .payment_method import PaymentMethod as StripePaymentMethod

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY


class NoDefaultPaymentMethodError(Exception):
    """Raised when there is no default payment method for the customer."""

    def __init__(self, invoice_id: str, customer_id: str, user_address_id: str):
        self.invoice_id = invoice_id
        self.customer_id = customer_id
        self.user_address_id = user_address_id

    def __str__(self):
        return f"NoDefaultPaymentMethodError: [invoice_id:{self.invoice_id}]-[customer_id:{self.customer_id}]-[user_address_id:{self.user_address_id}]"


class NoPaymentMethodIDInMetadataError(Exception):
    """Raised when there is no payment method ID in the Stripe PaymentMethod metadata."""

    def __init__(
        self,
        invoice_id: str,
        customer_id: str,
        user_address_id: str,
        payment_method_id: str,
    ):
        self.invoice_id = invoice_id
        self.customer_id = customer_id
        self.user_address_id = user_address_id
        self.payment_method_id = payment_method_id

    def __str__(self):
        return f"NoPaymentMethodIDInMetadataError: [invoice_id:{self.invoice_id}]-[customer_id:{self.customer_id}]-[user_address_id:{self.user_address_id}]-[payment_method_id:{self.payment_method_id}]"


class Invoice:
    @staticmethod
    def get_all(customer_id: str = None):
        has_more = True
        starting_after = None
        data: List[stripe.Invoice] = []
        while has_more:
            invoices = (
                stripe.Invoice.list(
                    limit=100,
                    starting_after=starting_after,
                    customer=customer_id,
                )
                if customer_id
                else stripe.Invoice.list(
                    limit=100,
                    starting_after=starting_after,
                )
            )

            data = data + list(invoice.to_dict() for invoice in invoices["data"])
            has_more = invoices["has_more"]
            print(f"has_more: {has_more}")
            print(f"len(data): {len(data)}")
            print(f"starting_after: {data[-1]['id']}" if has_more else "No more")
            starting_after = data[-1]["id"] if len(data) > 0 else None
        return data

    @staticmethod
    def get(id: str):
        return stripe.Invoice.retrieve(id)

    @staticmethod
    def finalize(invoice_id: str):
        return stripe.Invoice.finalize_invoice(invoice_id)

    @staticmethod
    def attempt_pay_og(invoice_id: str, payment_method: str = None):
        try:
            invoice = (
                stripe.Invoice.pay(invoice_id)
                if not payment_method
                else stripe.Invoice.pay(
                    invoice_id,
                    payment_method=payment_method,
                )
            )
            return True if invoice.status == "paid" else False
        except Exception as e:
            logger.error(
                f"Invoice.attempt_pay_og: [invoice_id:{invoice_id}]-[payment_method:{payment_method}][{e}]",
                exc_info=e,
            )
            return False

    @staticmethod
    def attempt_pay(invoice_id: str):
        # Import here to avoid circular import of partially initialized module api.module.
        from api.models import UserAddress
        from payment_methods.models.payment_method import (
            PaymentMethod as DownstreamPaymentMethod,
        )

        downstream_payment_method = None
        user_address_id = None
        downstream_payment_method_id = None
        try:
            # Get the Stripe Invoice object.
            invoice = stripe.Invoice.retrieve(invoice_id)

            # Get the Stripe Customer object.
            customer = Customer.get(invoice["customer"])

            # Get the Downstream UserAddress object.
            user_address = UserAddress.objects.get(
                stripe_customer_id=invoice["customer"]
            )
            user_address_id = str(user_address.id)

            if customer.invoice_settings.default_payment_method:
                # Get the Stripe PaymentMethod object.
                payment_method = StripePaymentMethod.get(
                    customer.invoice_settings.default_payment_method,
                )

                # Get the Downstream PaymentMethod object.
                downstream_payment_method_id = payment_method["metadata"].get(
                    "payment_method_id", None
                )
                if downstream_payment_method_id is not None:
                    downstream_payment_method = DownstreamPaymentMethod.objects.get(
                        id=downstream_payment_method_id
                    )
                else:
                    raise NoPaymentMethodIDInMetadataError(
                        invoice.id, customer.id, user_address_id, payment_method.id
                    )
            else:
                raise NoDefaultPaymentMethodError(
                    invoice.id, customer.id, user_address_id
                )
            # Check if the Downstream PaymentMethod is active.
            if downstream_payment_method.active:
                # Pay the Stripe Invoice using the default PaymentMethod.
                invoice = stripe.Invoice.pay(invoice_id, payment_method=payment_method)
                return True if invoice.status == "paid" else False
        except NoPaymentMethodIDInMetadataError as e:
            # Stripe PaymentMethod metadata does not contain the Downstream PaymentMethod ID.
            logger.error(f"Invoice.attempt_pay: try attempt_pay_og [{e}]", exc_info=e)
            return Invoice.attempt_pay_og(
                invoice_id,
                payment_method=customer.invoice_settings.default_payment_method,
            )
        except NoDefaultPaymentMethodError as e:
            # No default payment method for the customer.
            logger.error(f"Invoice.attempt_pay: try attempt_pay_og [{e}]", exc_info=e)
            return Invoice.attempt_pay_og(
                invoice_id,
                payment_method=customer.invoice_settings.default_payment_method,
            )
        except DownstreamPaymentMethod.DoesNotExist as e:
            # Downstream PaymentMethod does not exist.
            logger.error(
                f"Invoice.attempt_pay:DownstreamPaymentMethod.DoesNotExist: try attempt_pay_og [invoice_id:{invoice_id}]-[user_address.id:{user_address.id}]-[downstream_payment_method_id:{downstream_payment_method_id}]-[{e}]",
                exc_info=e,
            )
            return Invoice.attempt_pay_og(
                invoice_id,
                payment_method=customer.invoice_settings.default_payment_method,
            )
        except stripe.error.CardError as e:
            # https://docs.stripe.com/api/errors
            # Since it's a decline, stripe.error.CardError will be caught
            # TODO: Maybe, add allowed CardErrors. An allowed error would not set the PaymentMethod to inactive.
            downstream_payment_method.active = False
            downstream_payment_method.reason = f"Invoice.attempt_pay:CardError: [user_address.id:{user_address.id}]-[{e}]-[type:{e.code}]-[param:{e.param}]"
            downstream_payment_method.save()
            logger.error(
                f"Invoice.attempt_pay:CardError: [invoice_id:{invoice_id}]-[user_address.id:{user_address.id}]-[{e}]-[{e.code}]-[{e.param}]",
                exc_info=e,
            )
            downstream_payment_method.send_internal_email(user_address)
        except stripe.error.RateLimitError as e:
            # Too many requests made to the API too quickly
            logger.error(
                f"Invoice.attempt_pay:stripe.RateLimitError: [invoice_id:{invoice_id}]-[{e}]",
                exc_info=e,
            )
        except stripe.error.InvalidRequestError as e:
            # Invalid parameters were supplied to Stripe's API
            logger.error(
                f"Invoice.attempt_pay:stripe.InvalidRequestError: [invoice_id:{invoice_id}]-[user_address.id:{user_address_id}]-[downstream_payment_method_id:{downstream_payment_method_id}]-[{e}]",
                exc_info=e,
            )
        except stripe.error.AuthenticationError as e:
            # Authentication with Stripe's API failed (maybe the API keys changed recently)
            logger.error(
                f"Invoice.attempt_pay:stripe.AuthenticationError: [invoice_id:{invoice_id}]-[{e}]",
                exc_info=e,
            )
        except stripe.error.APIConnectionError as e:
            # Network communication with Stripe failed
            logger.error(
                f"Invoice.attempt_pay:stripe.APIConnectionError: [invoice_id:{invoice_id}]-[{e}]",
                exc_info=e,
            )
        except stripe.error.StripeError as e:
            # Display a very generic error to the user, and maybe send yourself an email
            logger.error(
                f"Invoice.attempt_pay:stripe.StripeError: [invoice_id:{invoice_id}]-[user_address.id:{user_address_id}]-[downstream_payment_method_id:{downstream_payment_method_id}]-[{e}]",
                exc_info=e,
            )
        except Exception as e:
            # Something else happened, completely unrelated to Stripe.
            logger.error(
                f"Invoice.attempt_pay:stripe.StripeError: [invoice_id:{invoice_id}]-[user_address.id:{user_address_id}]-[downstream_payment_method_id:{downstream_payment_method_id}]-[{e}]",
                exc_info=e,
            )

        return False

    @staticmethod
    def send_invoice(invoice_id: str):
        return stripe.Invoice.send_invoice(invoice_id)
