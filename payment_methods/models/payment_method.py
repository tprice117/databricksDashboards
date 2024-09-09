import re
import threading
from django.conf import settings
from django.db import models
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.template.loader import render_to_string
import logging
from stripe import CardError
from api.models import User, UserGroup
from api.models.user.user_address import UserAddress
from common.models import BaseModel
from common.utils.stripe.stripe_utils import StripeUtils
from payment_methods.utils import DSPaymentMethods
from notifications.utils.add_email_to_queue import add_internal_email_to_queue

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
    )
    active = models.BooleanField(default=True)
    reason = models.TextField(blank=True, null=True)

    @property
    def card_number(self):
        response = self.get_card()
        return (
            response["data"]["number"]
            if response and "data" in response and "number" in response["data"]
            else None
        )

    @property
    def card_brand(self):
        response = self.get_card()
        return (
            response["data"]["brand"]
            if response and "data" in response and "brand" in response["data"]
            else None
        )

    @property
    def card_exp_month(self):
        response = self.get_card()
        return (
            response["data"]["expiration_month"]
            if response
            and "data" in response
            and "expiration_month" in response["data"]
            else None
        )

    @property
    def card_exp_year(self):
        response = self.get_card()
        return (
            response["data"]["expiration_year"]
            if response and "data" in response and "expiration_year" in response["data"]
            else None
        )

    def get_card(self):
        return DSPaymentMethods.Tokens.get_card(self.token)

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
                add_internal_email_to_queue(
                    from_email="system@trydownstream.com",
                    additional_to_emails=[
                        "mwickey@trydownstream.com",
                        "billing@trydownstream.com",
                    ],
                    subject=subject,
                    html_content=html_content,
                )
            except Exception as e:
                logger.error(f"PaymentMethod.send_internal_email: [{e}]", exc_info=e)


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

    # Sync the Payment Method with Stripe.
    # Note: This is done asynchronously because it is not critical.
    p = threading.Thread(target=instance.sync_stripe_payment_method)
    p.start()
