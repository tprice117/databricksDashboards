from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver

from api.models import Order
from api.models.day_of_week import DayOfWeek
from api.models.order.order_group_seller_decline import OrderGroupSellerDecline
from api.models.seller.seller_product_seller_location import SellerProductSellerLocation
from api.models.service_recurring_freqency import ServiceRecurringFrequency
from api.models.time_slot import TimeSlot
from api.models.user.user_address import UserAddress
from api.models.waste_type import WasteType
from chat.models.conversation import Conversation
from common.models import BaseModel
from matching_engine.utils import MatchingEngine


class OrderGroup(BaseModel):
    class Status(models.TextChoices):
        PENDING = "PENDING"
        IN_PROGRESS = "IN-PROGRESS"
        INVOICED = "INVOICED"
        PAST_DUE = "PAST DUE"

    user = models.ForeignKey("api.User", models.PROTECT)
    user_address = models.ForeignKey(
        UserAddress,
        models.PROTECT,
        related_name="order_groups",
    )
    seller_product_seller_location = models.ForeignKey(
        SellerProductSellerLocation,
        models.PROTECT,
        related_name="order_groups",
    )
    conversation = models.ForeignKey(
        Conversation,
        models.CASCADE,
        blank=True,
    )
    # https://developers.intercom.com/docs/build-an-integration/learn-more/rest-apis/identifiers-and-urls/
    intercom_id = models.CharField(
        max_length=128,
        blank=True,
        null=True,
        help_text="The Intercom ID of the Conversation object.",
    )
    waste_type = models.ForeignKey(WasteType, models.PROTECT, blank=True, null=True)
    time_slot = models.ForeignKey(TimeSlot, models.PROTECT, blank=True, null=True)
    access_details = models.TextField(blank=True, null=True)
    placement_details = models.TextField(blank=True, null=True)
    service_recurring_frequency = models.ForeignKey(
        ServiceRecurringFrequency, models.PROTECT, blank=True, null=True
    )
    preferred_service_days = models.ManyToManyField(DayOfWeek, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    take_rate = models.DecimalField(max_digits=18, decimal_places=2, default=30)
    tonnage_quantity = models.IntegerField(blank=True, null=True)
    delivery_fee = models.DecimalField(
        max_digits=18, decimal_places=2, default=0, blank=True, null=True
    )
    removal_fee = models.DecimalField(
        max_digits=18, decimal_places=2, default=0, blank=True, null=True
    )

    def __str__(self):
        return f'{self.user.user_group.name if self.user.user_group else ""} - {self.user.email} - {self.seller_product_seller_location.seller_location.seller.name}'

    @property
    def status(self):
        # Get all Orders for this OrderGroup.
        orders = self.orders.all()

        # Get any OrderLineItems that are Paid = False and stripe_invoice_line_item_id is not None.
        unpaid_invoiced_order_line_items = []
        for order in orders:
            for order_line_item in order.order_line_items.all():
                if (
                    order_line_item.stripe_invoice_line_item_id
                    and not order_line_item.paid
                ):
                    unpaid_invoiced_order_line_items.append(order_line_item)

        # If there are any unpaid invoiced OrderLineItems, then the OrderGroup is INVOICED.
        if len(unpaid_invoiced_order_line_items) > 0:
            return OrderGroup.Status.INVOICED

        # Sort Orders by EndDate (most recent first).
        orders = orders.order_by("-end_date")

        # If there are no Orders, then the OrderGroup is PENDING.
        order_group_status = OrderGroup.Status.PENDING
        for order in orders:
            if order.status == Order.Status.SCHEDULED:
                order_group_status = OrderGroup.Status.IN_PROGRESS
                break

        return order_group_status

    def update_pricing(self):
        """
        Based on the OrderGroup.SellerProductSellerLocation's pricing, update the pricing.
        """
        # Update the Delivery Fee and Removal Fee.
        self.delivery_fee = self.seller_product_seller_location.delivery_fee
        self.removal_fee = self.seller_product_seller_location.removal_fee

        # Update tonnage_quantity.
        seller_product_seller_location_material_waste_type = (
            self.seller_product_seller_location.material.waste_types.filter(
                waste_type=self.waste_type
            ).first()
        )

        self.tonnage_quantity = (
            seller_product_seller_location_material_waste_type.tonnage_included
        )

        self.save()

    def can_seller_decline(self):
        # Ensure that the only Order in the OrderGroup has a TYPE of DELIVERY. Also, ensure
        # that the status of the Order is PENDING.
        if (
            self.orders.count() == 1
            and self.orders.first().type == Order.Type.DELIVERY
            and self.orders.first().status == Order.Status.PENDING
        ):
            return True
        else:
            return False

    def seller_decline(self):
        """
        If the Seller can decline the OrderGroup, then:
            1) Find the "next" SellerProductSellerLocation for OrderGroup.
            2) Create an OrderGroupSellerDecline object for the SellerProductSellerLocation.
            3a) If a "next" SellerProductSellerLocation is found, then:
                a) Reassign the OrderGroup to the new SellerProductSellerLocation.
                b) Update the Pricing of the OrderGroup (keeping the Customer pricing the same).
                c) Recreate the Order (keeping the Customer pricing the same).
            3b) If a "next" SellerProductSellerLocation is not found, then:
                c) Do nothing else, the Status of the OrderGroup will be computed as REASSIGNING.
        """
        if self.can_seller_decline():
            # Find the "next" SellerProductSellerLocation for the OrderGroup.
            next_seller_product_seller_location = (
                MatchingEngine.rematch_seller_product_seller_location(
                    order_group=self,
                )
            )

            # Create an OrderGroupSellerDecline object.
            OrderGroupSellerDecline.objects.create(
                order_group=self,
                seller_product_seller_location=self.seller_product_seller_location,
            )

            # Either reassign the OrderGroup to the new SellerProductSellerLocation
            # or set the OrderGroup status to REASSIGNING.
            if next_seller_product_seller_location:
                # Reassign the OrderGroup to the new SellerProductSellerLocation.
                self.seller_product_seller_location = (
                    next_seller_product_seller_location
                )

                # Update the Pricing of the OrderGroup.
                self.update_pricing()

                # Update the Pricing of the OrderGroup.Service, OrderGroup.Rental,
                # and OrderGroup.Material.
                if hasattr(self, "rental"):
                    self.rental.update_pricing()

                if hasattr(self, "material"):
                    self.material.update_pricing()

                if hasattr(self, "service"):
                    self.service.update_pricing()

                # Update the Pricing of the DELIVERY Order.
                order = self.orders.first()
                order.update_pricing()

                self.save()

            else:
                # Set the OrderGroup status to CANCELLED.
                self.status = Order.Status.CANCELLED
                self.save()


@receiver(pre_save, sender=OrderGroup)
def pre_save_order_group(sender, instance: OrderGroup, *args, **kwargs):

    # If the OrderGroup is being created, then create a Conversation for
    # the OrderGroup.
    if instance._state.adding:
        instance.conversation = Conversation.objects.create()
        # TODO: Create a Conversation in Intercom for the OrderGroup.
    # TODO: On OrderGroup complete, maybe close the Conversation in Intercom.
    # https://developers.intercom.com/docs/references/rest-api/api.intercom.io/conversations/manageconversation
