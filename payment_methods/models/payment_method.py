import logging
import re
import threading
from typing import Optional

import stripe
from django.conf import settings
from django.db import models
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.template.loader import render_to_string
from stripe import CardError

from api.models import User, UserGroup
from api.models.user.user_address import UserAddress
from common.models import BaseModel
from common.utils.stripe.stripe_utils import StripeUtils
from notifications.utils.add_email_to_queue import add_internal_email_to_queue
from payment_methods.utils import DSPaymentMethods
from payment_methods.utils.detect_card_type import detect_card_type

logger = logging.getLogger(__name__)


class PaymentMethod(BaseModel):
    token = models.CharField(max_length=255)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
    )
    user_group = models.ForeignKey(
        UserGroup,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    active = models.BooleanField(default=True)
    reason = models.TextField(blank=True, null=True)

    def __str__(self):
        if self.active:
            return f"{self.id} - active"
        else:
            return f"{self.id} - inactive: {self.inactive_reason}"

    @property
    def card_number(self):
        """Return all the digits with * except the last 4 digits."""
        response = self.get_card()
        return response["number"]

    @property
    def card_brand(self):
        response = self.get_card()
        return response["brand"]

    @property
    def card_exp_month(self):
        response = self.get_card()
        return response["expiration_month"]

    @property
    def card_exp_year(self):
        response = self.get_card()
        return response["expiration_year"]

    def get_card(self):
        """Returns CreditCardType with the card number masked.
        {"number": "******1111", "brand": "", ""expiration_month": 12, "expiration_year": 2023}
        payment_methods.api.v1.serializers.payment_method.CreditCardType
        Not imported to avoid circular import."""
        response = None
        try:
            response = DSPaymentMethods.Tokens.get_card(self.token)
        except Exception as e:
            pass
        card = {
            "number": None,
            "brand": None,
            "expiration_month": None,
            "expiration_year": None,
        }
        if response and "data" in response and "number" in response["data"]:
            card["number"] = re.sub(r"\d(?=\d{4})", "*", response["data"]["number"])
            card["brand"] = detect_card_type(response["data"]["number"])
        if (
            card["brand"] is None
            and response
            and "data" in response
            and "brand" in response["data"]
        ):
            card["brand"] = response["data"]["brand"]
        if response and "data" in response and "expiration_month" in response["data"]:
            card["expiration_month"] = response["data"]["expiration_month"]
        if response and "data" in response and "expiration_year" in response["data"]:
            card["expiration_year"] = response["data"]["expiration_year"]
        return card

    @property
    def inactive_reason(self):
        if self.reason:
            pattern = r"\[Request req_[\w:]+: (.*?)\]-"
            match = re.search(pattern, self.reason)
            if match:
                return match.group(1)
            else:
                return None
        else:
            return None

    def create_stripe_payment_method(self):
        """
        Create a Stripe Payment Method with the token (via
        Basis Theory Reactor).
        """
        return DSPaymentMethods.Reactors.invoke(
            reactor_id=settings.BASIS_THEORY_CREATE_PAYMENT_METHOD_REACTOR_ID,
            args={
                "token": self.token,
                "payment_method_id": str(self.id),
            },
        )

    def sync_stripe_payment_method(self, user_address: UserAddress = None):
        """
        Sync the Payment Method with Stripe according to the
        UserGroup and associated UserAddresses.
        """
        if self.active:
            # For the Payment Method UserGroup, find any UserAddresses
            # (Stripe Customers) that don't have the Payment Method
            # (see the payment_method.metadata["token"]).
            user_addresses = (
                self.user_group.user_addresses.all()
                if not user_address
                else [user_address]
            )

            # Iterate over all UserAddresses and sync them with Stripe.
            user_address: UserAddress
            for user_address in user_addresses:
                # Get all Payment Methods for the UserAddress.
                stripe_customer_payment_methods = StripeUtils.PaymentMethod.list(
                    customer_id=user_address.stripe_customer_id,
                )
                # Check if the Payment Method is already synced with Stripe
                # for the UserAddress.
                stripe_payment_method = next(
                    (
                        method
                        for method in stripe_customer_payment_methods
                        if method.get("metadata", {}).get("token") == self.token
                    ),
                    None,
                )
                # print("stripe_payment_method": stripe_payment_method)

                if stripe_payment_method:
                    print("stripe_payment_method already exists")
                else:
                    print("stripe_payment_method DOES NOT exist", user_address.id)

                # If the Payment Method is not already synced with Stripe
                # for the UserAddress, create it.
                if not stripe_payment_method:
                    try:
                        response = self.create_stripe_payment_method()

                        # Add the Payment Method to the UserAddress/Stripe Customer.
                        StripeUtils.PaymentMethod.attach(
                            payment_method_id=response["raw"],
                            customer_id=user_address.stripe_customer_id,
                        )
                        print("stripe_payment_method created")
                    except CardError as e:
                        self.active = False
                        self.reason = f"sync_stripe_payment_method:CardError: [user_address.id:{user_address.id}]-[{e}]-[type:{e.code}]-[param:{e.param}]"
                        self.save()
                        logger.error(
                            f"PaymentMethod.sync_stripe_payment_method:CardError: [user_address.id:{user_address.id}]-[{e}]-[{e.code}]-[{e.param}]-[payment_method_id:{self.id}]",
                            exc_info=e,
                        )
                        self.send_internal_email(user_address)
                        break
                    except Exception as e:
                        print(
                            f"PaymentMethod.sync_stripe_payment_method: [user_address.id:{user_address.id}]-[{e}]-[payment_method_id:{self.id}]"
                        )
                        # NOTE: There seems to be inconsistency on a BasisTheory PaymentRequired error,
                        # sometimes it shows and other times it doesn't.
                        # logger.info(
                        #     f"PaymentMethod.sync_stripe_payment_method: [user_address.id:{user_address.id}]-[{e}]-[payment_method_id:{self.id}]",
                        #     exc_info=e,
                        # )
                        # if hasattr(e, "body"):
                        #     if isinstance(e.body, str) and e.body.find(
                        #         "Invalid Payment Method"
                        #     ):
                        #         self.reason = f"PaymentMethod.sync_stripe_payment_method: [user_address.id:{user_address.id}]-[{e.body}]"
                        #         self.active = False
                        #         self.save()
                        #         self.send_internal_email(user_address)
                        #         break

    def send_internal_email(self, user_address: UserAddress):
        # Send email to internal team. Only on our PROD environment.
        if settings.ENVIRONMENT == "TEST":
            try:
                subject = f"Payment Method Error: {user_address.user_group.name}-{user_address.formatted_address()}"
                payment_method_link = f"{settings.API_URL}/admin/payment_methods/paymentmethod/{str(self.id)}/change/"
                payload = {
                    "user_address": user_address,
                    "reason": self.reason,
                    "payment_method": self,
                    "payment_method_link": payment_method_link,
                }
                html_content = render_to_string(
                    "emails/internal/bad-payment-method.min.html", payload
                )
                additional_to_emails = [
                    "mwickey@trydownstream.com",
                    "dleyden@trydownstream.com",
                    "ctorgerson@trydownstream.com",
                    "hrobbins@trydownstream.com",
                    "billing@trydownstream.com",
                ]
                if user_address.user_group and user_address.user_group.account_owner:
                    # Send to the account owner.
                    additional_to_emails.append(
                        user_address.user_group.account_owner.email
                    )
                add_internal_email_to_queue(
                    from_email="system@trydownstream.com",
                    additional_to_emails=additional_to_emails,
                    subject=subject,
                    html_content=html_content,
                )
            except Exception as e:
                logger.error(f"PaymentMethod.send_internal_email: [{e}]", exc_info=e)

    def get_stripe_payment_method(
        self,
        user_address: UserAddress,
    ) -> Optional[stripe.PaymentMethod]:
        """
        Get the Stripe Payment Method for passed UserAddress.
        """
        # Get all Payment Methods for the UserAddress.
        stripe_payment_methods = StripeUtils.PaymentMethod.list(
            customer_id=user_address.stripe_customer_id,
        )

        # Get the StripePayementMethod for the passed PaymentMethod
        # (match on the metadata["payment_method_id"]) or None.
        return next(
            (
                stripe_payment_method
                for stripe_payment_method in stripe_payment_methods
                if stripe_payment_method["metadata"].get("payment_method_id")
                == str(self.id)
            ),
            None,
        )

    def set_stripe_default_payment_method(self, user_address: UserAddress):
        """
        Set the default payment method for the UserAddress in Stripe.
        return: Stripe PaymentMethod or None on failure.
        """
        # Get the Stripe PaymentMethod for the Downstream PaymentMethod.
        stripe_payment_method = self.get_stripe_payment_method(user_address)
        if stripe_payment_method:
            # Update the Stripe Customer with the new DefaultPaymentMethod.
            StripeUtils.Customer.ensure_default_payment_method(
                user_address.stripe_customer_id,
                payment_method_id=stripe_payment_method["id"],
            )
        else:
            # The Downstream PaymentMethod is not found in Stripe.
            # Try syncing the Downstream PaymentMethods for this UserAddress to Stripe.
            self.sync_stripe_payment_method(user_address=user_address)
            # Re-fetch the Stripe PaymentMethod.
            stripe_payment_method = self.get_stripe_payment_method(user_address)
        return stripe_payment_method


@receiver(post_save, sender=PaymentMethod)
def save_payment_method(sender, instance: PaymentMethod, created, **kwargs):
    # Note: This is done asynchronously because it is not critical.
    p = threading.Thread(target=instance.sync_stripe_payment_method)
    p.start()


@receiver(pre_delete, sender=PaymentMethod)
def delete_payment_method(sender, instance: PaymentMethod, using, **kwargs):
    if instance.user_group:
        payment_methods = PaymentMethod.objects.filter(
            user_group_id=instance.user_group.id
        )
    else:
        payment_methods = PaymentMethod.objects.filter(user_id=instance.user.id)
    if payment_methods.count() == 1:
        raise ValueError(
            "Cannot delete the last Payment Method for the UserGroup/User."
        )
    # Delete the token from Basis Theory.
    DSPaymentMethods.Tokens.delete(instance.token)

    # If this card is used as a default payment in Stripe, then update the default payment method.
    stripe_payment_method = instance.get_stripe_payment_method()
    if stripe_payment_method:
        StripeUtils.PaymentMethod.detach(stripe_payment_method["id"])
        # NOTE: If this payment method is the default payment method on Stripe,
        # then it will be updated on the next invoice pay attempt or on the nightly payment sync.

    # Remove the Payment Method from all UserAddresses.
    UserAddress.objects.filter(default_payment_method=instance).update(
        default_payment_method=None
    )

    # Sync the Payment Method with Stripe.
    # Note: This is done asynchronously because it is not critical.
    p = threading.Thread(target=instance.sync_stripe_payment_method)
    p.start()
