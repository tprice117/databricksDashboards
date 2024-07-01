from django.db import models
from django.db.models import Q
from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete

from api.models.seller.seller_location import SellerLocation
from api.models.user.user import User
from api.models.order.order import Order
from common.models import BaseModel
from communications.intercom.conversation import Conversation as IntercomConversation


class UserSellerLocation(BaseModel):
    user = models.ForeignKey(User, models.CASCADE)
    seller_location = models.ForeignKey(SellerLocation, models.CASCADE)

    class Meta:
        unique_together = ("user", "seller_location")

    def __str__(self):
        return f"{self.user.email} - {self.seller_location.name}"


def get_all_active_orders_with_conversations(seller_location: SellerLocation):
    # Get all order_groups for this seller_location, have intercom_id set, and have orders that are either pending or scheduled.
    return (
        Order.objects.filter(
            order_group__seller_product_seller_location__seller_location_id=seller_location.id
        )
        .filter(Q(status=Order.Status.PENDING) | Q(status=Order.Status.SCHEDULED))
        .filter(order_group__intercom_id__isnull=False)
        .distinct("order_group")
        .select_related("order_group")
    )


@receiver(post_save, sender=UserSellerLocation)
def user_seller_location_post_save(
    sender, instance: UserSellerLocation, *args, **kwargs
):
    # Add user from all pending/scheduled order conversations of this seller_location.
    orders = get_all_active_orders_with_conversations(instance.seller_location)
    for order in orders:
        IntercomConversation.attach_users_conversation(
            [instance.user], order.order_group.intercom_id
        )


@receiver(post_delete, sender=UserSellerLocation)
def user_seller_location_post_delete(
    sender, instance: UserSellerLocation, *args, **kwargs
):
    # Remove user from all pending/scheduled order conversations of this seller_location.
    orders = get_all_active_orders_with_conversations(instance.seller_location)
    for order in orders:
        IntercomConversation.detach_users_conversation(
            [instance.user], order.order_group.intercom_id
        )
