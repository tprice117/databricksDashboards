from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.db import models
from django.template.loader import render_to_string
from common.models import BaseModel
from api.models.track_data import track_data
from payment_methods.models.payment_method import PaymentMethod
from notifications.utils.add_email_to_queue import add_email_to_queue


@track_data(
    "payment_method",
    "pay_later",
    "quote_accepted_at",
    "customer_price",
    "seller_price",
)
class CartOrder(BaseModel):
    """A CartOrder is a single location with one or more transactions (api.Order)."""

    cart = models.ForeignKey("cart.Cart", models.CASCADE, related_name="cart_orders")
    user_address = models.ForeignKey(
        "api.UserAddress", models.CASCADE, related_name="cart_orders"
    )
    # Foreign key to cart in Order model with related_name="orders".
    # Either a payment method or pay later.
    payment_method = models.ForeignKey(
        PaymentMethod, models.CASCADE, related_name="cart_orders", blank=True, null=True
    )
    pay_later = models.BooleanField(default=False)
    quote = models.JSONField(
        blank=True, null=True, help_text="Quote json from get_quote_data."
    )
    take_rate = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=30,
        help_text="Take rate is from OrderGroup.",
    )
    customer_price = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    seller_price = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    to_emails = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Comman separated emails to send quote to.",
    )
    subject = models.CharField(
        max_length=255, blank=True, null=True, help_text="Subject for the email."
    )
    quote_expiration = models.DateTimeField(blank=True, null=True)
    quote_accepted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"

    def __str__(self):
        return str(self.user_address)


@receiver(post_save, sender=CartOrder)
def on_cart_post_save(sender, cart_order: CartOrder, created, **kwargs):
    """Sends an email to person who created the Cart Order when quote
    has been accepted."""

    if cart_order.quote_accepted_at is not None:
        if cart_order.old_value("quote_accepted_at") is None:
            # Send the sale person an email.
            subject = f"Quote Accepted! [{cart_order.subject}]"
            quote_link = (
                f"{settings.API_URL}/customer/cart/quote/?quote_id={cart_order.id}"
            )
            payload = {
                "user_address": cart_order.user_address,
                "total": cart_order.customer_price,
                "quote_link": quote_link,
            }
            html_content = render_to_string(
                "customer_dashboard/emails/accepted_quote.min.html", payload
            )
            add_email_to_queue(
                from_email="dispatch@trydownstream.com",
                to_emails=[cart_order.created_by.email],
                subject=subject,
                html_content=html_content,
                reply_to="dispatch@trydownstream.com",
            )
