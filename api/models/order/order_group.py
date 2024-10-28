import logging
import uuid

from django.core.files.base import ContentFile
from django.db import models
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from api.models import Order
from api.models.day_of_week import DayOfWeek
from api.models.main_product.main_product import MainProduct
from api.models.order.order_group_material import OrderGroupMaterial
from api.models.order.order_group_material_waste_type import OrderGroupMaterialWasteType
from api.models.order.order_group_rental import OrderGroupRental
from api.models.order.order_group_rental_multi_step import OrderGroupRentalMultiStep
from api.models.order.order_group_rental_multi_step_shift import (
    OrderGroupRentalMultiStepShift,
)
from api.models.order.order_group_rental_one_step import OrderGroupRentalOneStep
from api.models.order.order_group_seller_decline import OrderGroupSellerDecline
from api.models.order.order_group_service import OrderGroupService
from api.models.order.order_group_service_times_per_week import (
    OrderGroupServiceTimesPerWeek,
)
from api.models.seller.seller_product_seller_location import SellerProductSellerLocation
from api.models.service_recurring_freqency import ServiceRecurringFrequency
from api.models.time_slot import TimeSlot
from api.models.track_data import track_data
from api.models.user.user_address import UserAddress
from api.models.waste_type import WasteType
from api.utils.agreements.generate_agreement import generate_agreement_pdf
from chat.models.conversation import Conversation
from common.models import BaseModel
from common.utils import DistanceUtils
from common.utils.file_field.get_uuid_file_path import get_uuid_file_path
from common.utils.generate_code import save_unique_code
from matching_engine.matching_engine import MatchingEngine

logger = logging.getLogger(__name__)


@track_data(
    "agreement_signed_by",
    "agreement_signed_on",
)
class OrderGroup(BaseModel):
    class Status(models.TextChoices):
        PENDING = "PENDING"
        IN_PROGRESS = "IN-PROGRESS"
        INVOICED = "INVOICED"
        PAST_DUE = "PAST DUE"

    class ShiftCount(models.IntegerChoices):
        """
        For multi-step rentals, this field contains the number
        of daily working shifts the customer plans to use the equiptment for.
        """

        ONE_SHIFT = 1
        TWO_SHIFTS = 2
        THREE_SHIFTS = 3

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
    times_per_week = models.SmallIntegerField(
        blank=True,
        null=True,
        help_text="Service times times per week for MainProducts that have "
        "has_service_times_per_week.",
    )
    shift_count = models.IntegerField(
        choices=ShiftCount.choices,
        blank=True,
        null=True,
        help_text="For multi-step rentals, this field contains the number of daily "
        "working shifts the customer plans to use the equiptment for.",
    )
    delivery_fee = models.DecimalField(
        max_digits=18, decimal_places=2, default=0, blank=True, null=True
    )
    removal_fee = models.DecimalField(
        max_digits=18, decimal_places=2, default=0, blank=True, null=True
    )
    code = models.CharField(
        max_length=8,
        unique=True,
        blank=True,
        null=True,
        help_text="Unique code for the Order.",
    )
    agreement = models.FileField(
        upload_to=get_uuid_file_path,
        blank=True,
        null=True,
    )
    agreement_signed_by = models.ForeignKey(
        "api.User",
        models.PROTECT,
        blank=True,
        null=True,
        related_name="signed_agreements",
    )
    agreement_signed_on = models.DateTimeField(
        blank=True,
        null=True,
    )

    def __str__(self):
        return f'{self.user.user_group.name if self.user.user_group else ""} - {self.user.email} - {self.seller_product_seller_location.seller_location.seller.name}'

    class Meta:
        verbose_name = "Booking"
        verbose_name_plural = "Bookings"

    @property
    def get_code(self):
        return f"B-{self.code}"

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
                main_product_waste_type__waste_type=self.waste_type
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

    def create_delivery(self, delivery_date, schedule_window: str = None) -> Order:
        """Create a delivery or a one time for the OrderGroup.

        Args:
            delivery_date (date/date str): The delivery date.
            schedule_window (str): The preferred time window for the delivery.

        Returns:
            Order: Returns the delivery order object.
        """
        orders = self.orders.order_by("-created_on")
        if orders.count() == 0:
            order_group_start_equal = delivery_date == self.start_date
            if not order_group_start_equal:
                raise Exception(
                    f"Cannot create a delivery because Order has a different start date than OrderGroup [{delivery_date}!={self.start_date}]."
                )
            delivery_order = Order(
                order_group=self,
                start_date=delivery_date,
                end_date=delivery_date,
            )
            if schedule_window:
                delivery_order.schedule_window = schedule_window
            delivery_order.save()
        else:
            raise Exception(
                "Cannot create a delivery because OrderGroup already has an order, create swap instead."
            )
        return delivery_order

    @property
    def order_type(self):
        orders = self.orders.order_by("-created_on")
        if orders.count() == 0:
            return None
        else:
            last_order = orders.first()
            return last_order.order_type

    def create_swap(self, swap_date, schedule_window: str = None) -> Order:
        """Create a swap for the OrderGroup.

        Args:
            swap_date (date/date str): The swap/service date.
            schedule_window (str): The preferred time window for the swap.

        Raises:
            Exception: Raises an exception if this is the first order in the OrderGroup.

        Returns:
            Order: Returns the swap order object.
        """
        orders = self.orders.order_by("-created_on")
        if orders.count() == 0:
            raise Exception(
                "Cannot create a swap as first order for OrderGroup, create delivery instead."
            )
        else:
            last_order = orders.first()
            swap_order = Order(
                order_group=self, start_date=last_order.end_date, end_date=swap_date
            )
            if schedule_window:
                swap_order.schedule_window = schedule_window
            swap_order.save()
        return swap_order

    def create_removal(self, removal_date, schedule_window: str = None) -> Order:
        """Create a removal for the OrderGroup. This ends the OrderGroup
        i.e. This ends this current service rental.

        Args:
            removal_date (date/date str): The removal date.
            schedule_window (str): The preferred time window for the removal.

        Raises:
            Exception: Raises an exception if this is the first order in the OrderGroup.

        Returns:
            Order: Returns the removal order object.
        """
        orders = self.orders.order_by("-created_on")
        if orders.count() == 0:
            raise Exception(
                "Cannot create a removal as first order for OrderGroup, create delivery instead."
            )
        else:
            last_order = orders.first()
            if last_order.order_type == Order.Type.REMOVAL:
                raise Exception(
                    f"Cannot create a removal because last order is already a removal, set for {last_order.end_date}."
                )
            self.end_date = removal_date
            self.save()

            removal_order = Order(
                order_group=self, start_date=last_order.end_date, end_date=removal_date
            )
            if schedule_window:
                removal_order.schedule_window = schedule_window
            removal_order.save()
        return removal_order

    def generate_code(self):
        """Generate a unique code for the Order, if code is None."""
        if self.code is None:
            save_unique_code(self)

    def generate_agreement(self) -> ContentFile:
        """Generate an agreement for the OrderGroup."""
        pdf = generate_agreement_pdf(
            order_group=self,
        )

        return ContentFile(
            pdf.getvalue(),
            f"{uuid.uuid4()}.pdf",
        )

    @property
    def is_agreement_signed(self):
        return (
            self.agreement_signed_by is not None
            and self.agreement_signed_on is not None
        )


@receiver(pre_save, sender=OrderGroup)
def pre_save_order_group(sender, instance: OrderGroup, *args, **kwargs):
    # If the OrderGroup is being created, then create a Conversation for
    # the OrderGroup.
    if instance._state.adding:
        instance.conversation = Conversation.objects.create()
        # TODO: Create a Conversation in Intercom for the OrderGroup.
    # TODO: On OrderGroup complete, maybe close the Conversation in Intercom.
    # https://developers.intercom.com/docs/references/rest-api/api.intercom.io/conversations/manageconversation


@receiver(post_save, sender=OrderGroup)
def post_save(sender, instance: OrderGroup, created, **kwargs):
    if instance.code is None:
        instance.generate_code()

    # If creating, capture the SellerProductSellerLocation pricing
    # in the OrderGroup child objects.
    if created:
        main_product: MainProduct = (
            instance.seller_product_seller_location.seller_product.product.main_product
        )
        seller_product_seller_location: SellerProductSellerLocation = (
            instance.seller_product_seller_location
        )

        # Update included tonnage_quantity based on MainProduct.
        instance.tonnage_quantity = main_product.included_tonnage_quantity
        instance.save()

        # Rental One Step.
        if main_product.has_rental_one_step and hasattr(
            seller_product_seller_location, "rental_one_step"
        ):
            OrderGroupRentalOneStep.objects.create(
                order_group=instance,
                rate=seller_product_seller_location.rental_one_step.rate,
            )

        # Rental (two step).
        if main_product.has_rental and hasattr(
            seller_product_seller_location, "rental"
        ):
            OrderGroupRental.objects.create(
                order_group=instance,
                included_days=seller_product_seller_location.rental.included_days,
                price_per_day_included=seller_product_seller_location.rental.price_per_day_included,
                price_per_day_additional=seller_product_seller_location.rental.price_per_day_additional,
            )

        # Rental Multi Step.
        if main_product.has_rental_multi_step and hasattr(
            seller_product_seller_location, "rental_multi_step"
        ):
            OrderGroupRentalMultiStep.objects.create(
                order_group=instance,
                hour=seller_product_seller_location.rental_multi_step.hour,
                day=seller_product_seller_location.rental_multi_step.day,
                week=seller_product_seller_location.rental_multi_step.week,
                two_weeks=seller_product_seller_location.rental_multi_step.two_weeks,
                month=seller_product_seller_location.rental_multi_step.month,
            )

            # Rental Multi Step Shift (if exists).
            if hasattr(
                seller_product_seller_location.rental_multi_step,
                "rental_multi_step_shift",
            ):
                OrderGroupRentalMultiStepShift.objects.create(
                    order_group=instance,
                    two_shift=seller_product_seller_location.rental_multi_step.rental_multi_step_shift.two_shift,
                    three_shift=seller_product_seller_location.rental_multi_step.rental_multi_step_shift.three_shift,
                )

        # Material.
        if instance.waste_type:
            material_waste_type = (
                instance.seller_product_seller_location.material.waste_types.filter(
                    main_product_waste_type__waste_type=instance.waste_type
                ).first()
            )
            price_per_ton = 0
            tonnage_included = 0
            if material_waste_type:
                price_per_ton = material_waste_type.price_per_ton
                tonnage_included = material_waste_type.tonnage_included
                # Update the tonnage_quantity if SPSL has a higher tonnage_included.
                if tonnage_included > instance.tonnage_quantity:
                    instance.tonnage_quantity = tonnage_included
                    instance.save()
            # Create an OrderGroupMaterial.
            order_group_material = OrderGroupMaterial.objects.create(
                order_group=instance,
                # Only adding this so that the OrderGroupMaterialInline
                # in the admin will show the correct field values.
                price_per_ton=price_per_ton,
                tonnage_included=tonnage_included,
            )

            # For each SellerProductSellerLocationMaterialWasteType,
            # create an OrderGroupMaterialWasteType.
            for (
                material_waste_type
            ) in seller_product_seller_location.material.waste_types.all():
                OrderGroupMaterialWasteType.objects.create(
                    order_group_material=order_group_material,
                    main_product_waste_type=material_waste_type.main_product_waste_type,
                    price_per_ton=material_waste_type.price_per_ton,
                    tonnage_included=material_waste_type.tonnage_included,
                )

        # Service (legacy).
        if main_product.has_service and hasattr(
            seller_product_seller_location, "service"
        ):
            # Get distance between User and Seller.
            distance = DistanceUtils.get_euclidean_distance(
                instance.user_address.latitude,
                instance.user_address.longitude,
                instance.seller_product_seller_location.seller_location.latitude,
                instance.seller_product_seller_location.seller_location.longitude,
            )

            OrderGroupService.objects.create(
                order_group=instance,
                rate=seller_product_seller_location.service.price_per_mile
                or seller_product_seller_location.service.flat_rate_price,
                miles=(
                    distance
                    if distance
                    and seller_product_seller_location.service.price_per_mile
                    else None
                ),
            )

        # Service Times Per Week.
        if main_product.has_service_times_per_week and hasattr(
            seller_product_seller_location, "service_times_per_week"
        ):
            OrderGroupServiceTimesPerWeek.objects.create(
                order_group=instance,
                one_time_per_week=seller_product_seller_location.service_times_per_week.one_time_per_week,
                two_times_per_week=seller_product_seller_location.service_times_per_week.two_times_per_week,
                three_times_per_week=seller_product_seller_location.service_times_per_week.three_times_per_week,
                four_times_per_week=seller_product_seller_location.service_times_per_week.four_times_per_week,
                five_times_per_week=seller_product_seller_location.service_times_per_week.five_times_per_week,
            )

    # Generate agreement for the OrderGroup if:
    # 1) The agreement_signed_by or agreement_signed_on is None.
    # 2) The agreement_signed_by or agreement_signed_on has changed from None to not None.
    old_agreement_signed_by = instance.old_value("agreement_signed_by")
    old_agreement_signed_on = instance.old_value("agreement_signed_on")

    if (
        old_agreement_signed_by is None
        or old_agreement_signed_on is None
        or (
            old_agreement_signed_by is None
            and old_agreement_signed_on is None
            and instance.agreement_signed_by is not None
            and instance.agreement_signed_on is not None
        )
    ):
        instance.agreement = instance.generate_agreement()
        # Ensure the file is saved to the storage backend
        instance.agreement.save(
            instance.agreement.name, instance.agreement.file, save=False
        )
        # Update the database record without triggering the pre/post_save signals.
        OrderGroup.objects.filter(pk=instance.pk).update(agreement=instance.agreement)
