import datetime
from typing import List

from django.db import models
from django.db.models import Q
from django.db.models.signals import pre_save, post_save

from api.managers import UserAddressManager
from api.models.order.order import Order
from api.models.track_data import track_data
from api.models.user.user import User
from api.models.user.user_address_type import UserAddressType
from api.models.user.user_group import UserGroup
from api.utils.google_maps import geocode_address
from common.models import BaseModel
from common.utils.stripe.stripe_utils import StripeUtils
import logging

logger = logging.getLogger(__name__)


@track_data(
    "name",
    "project_id",
    "street",
    "city",
    "state",
    "postal_code",
    "country",
    "access_details",
    "autopay",
)
class UserAddress(BaseModel):
    user_group = models.ForeignKey(
        UserGroup,
        models.CASCADE,
        related_name="user_addresses",
        blank=True,
        null=True,
    )
    user = models.ForeignKey(
        User,
        models.CASCADE,
        blank=True,
        null=True,
    )
    user_address_type = models.ForeignKey(
        UserAddressType,
        models.CASCADE,
        blank=True,
        null=True,
    )
    default_payment_method = models.ForeignKey(
        "payment_methods.PaymentMethod",
        models.SET_NULL,
        blank=True,
        null=True,
    )
    stripe_customer_id = models.CharField(
        max_length=255,
        blank=True,
        unique=True,
    )
    name = models.CharField(max_length=255, blank=True, null=True)
    project_id = models.CharField(max_length=50, blank=True, null=True)
    street = models.TextField(blank=True, null=True)
    street2 = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=40)
    state = models.CharField(max_length=80)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=80)
    latitude = models.DecimalField(max_digits=18, decimal_places=15, blank=True)
    longitude = models.DecimalField(max_digits=18, decimal_places=15, blank=True)
    access_details = models.TextField(blank=True, null=True)
    autopay = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    allow_saturday_delivery = models.BooleanField(default=False)
    allow_sunday_delivery = models.BooleanField(default=False)

    # Managers
    objects = UserAddressManager()

    def __str__(self):
        return f"{(self.name or '[No Name]')} ({self.formatted_address()})"

    def formatted_address(self):
        return f"{self.street} {self.city}, {self.state} {self.postal_code}"

    def get_cart(self):
        """Get the cart orders for this address ordered by newest Booking/OrderGroup start date."""
        orders = Order.objects.filter(order_group__user_address_id=self.id)
        orders = orders.filter(submitted_on__isnull=True)
        orders = orders.prefetch_related("order_line_items")
        orders = orders.order_by("-order_group__start_date")
        return orders

    def update_stripe(self, save_on_update=False):
        try:
            # Populate Stripe Customer ID, if not already populated.
            if not self.stripe_customer_id:
                customer = StripeUtils.Customer.create()
                self.stripe_customer_id = customer.id
                if save_on_update:
                    UserAddress.objects.filter(id=self.id).update(
                        stripe_customer_id=customer.id
                    )
            else:
                try:
                    customer = StripeUtils.Customer.get(self.stripe_customer_id)
                except Exception as e:
                    # If the customer does not exist, create a new one.
                    customer = StripeUtils.Customer.create()
                    self.stripe_customer_id = customer.id
                    if save_on_update:
                        UserAddress.objects.filter(id=self.id).update(
                            stripe_customer_id=customer.id
                        )

            # Get "name" for UserGroup/B2C user.
            user_group_name = self.user_group.name if self.user_group else "[B2C]"

            customer = StripeUtils.Customer.update(
                customer.id,
                name=user_group_name + " | " + self.formatted_address(),
                email=(
                    self.user_group.billing.email
                    if self.user_group and hasattr(self.user_group, "billing")
                    else (self.user.email if self.user else None)
                ),
                # phone = self.user_group.billing.phone if hasattr(self.user_group, 'billing') else self.user.phone,
                shipping={
                    "name": self.name or self.formatted_address(),
                    "address": {
                        "line1": self.street,
                        "city": self.city,
                        "state": self.state,
                        "postal_code": self.postal_code,
                        "country": "US",
                    },
                },
                address={
                    "line1": (
                        self.user_group.billing.street
                        if self.user_group and hasattr(self.user_group, "billing")
                        else self.street
                    ),
                    "city": (
                        self.user_group.billing.city
                        if self.user_group and hasattr(self.user_group, "billing")
                        else self.city
                    ),
                    "state": (
                        self.user_group.billing.state
                        if self.user_group and hasattr(self.user_group, "billing")
                        else self.state
                    ),
                    "postal_code": (
                        self.user_group.billing.postal_code
                        if self.user_group and hasattr(self.user_group, "billing")
                        else self.postal_code
                    ),
                    "country": "US",
                    # "country": self.user_group.billing.country
                    # if hasattr(self.user_group, "billing")
                    # else self.country,
                },
                metadata={
                    "user_group_id": (
                        str(self.user_group.id) if self.user_group else None
                    ),
                    "user_address_id": str(self.id),
                    "user_id": str(self.user.id) if self.user else None,
                },
                tax_exempt=(
                    self.user_group.tax_exempt_status
                    if self.user_group and hasattr(self.user_group, "billing")
                    else UserGroup.TaxExemptStatus.NONE
                ),
            )
            return True
        except Exception as e:
            logger.error(f"Error updating Stripe Customer: {e}")
            return False

    def get_payment_method(self):
        """Get the default payment method for this address.
        If the address has a default payment method, use that,
        otherwise, use the default payment method for the user group, if it exists,
        otherwise, use the first active payment method for the user group."""
        from payment_methods.models import PaymentMethod

        if self.default_payment_method and self.default_payment_method.active:
            downstream_payment_method = self.default_payment_method
        elif (
            self.user_group
            and self.user_group.default_payment_method
            and self.user_group.default_payment_method.active
        ):
            downstream_payment_method = self.user_group.default_payment_method
        else:
            if self.user_group:
                # Check if UserGroup has another active PaymentMethod.
                downstream_payment_method = PaymentMethod.objects.filter(
                    user_group=self.user_group, active=True
                ).first()
            else:
                # Check if UserGroup has another active PaymentMethod.
                downstream_payment_method = PaymentMethod.objects.filter(
                    user=self.user, active=True
                ).first()

        return downstream_payment_method

    def pre_save(sender, instance, *args, **kwargs):
        # Only update latitude and longitude if the address has changed.
        if (
            instance._state.adding
            or instance.has_changed("street")
            or instance.has_changed("city")
            or instance.has_changed("state")
            or instance.has_changed("postal_code")
        ):
            # Populate latitude and longitude.
            latitude, longitude = geocode_address(
                f"{instance.street} {instance.city} {instance.state} {instance.postal_code}"
            )
            instance.latitude = latitude or 0
            instance.longitude = longitude or 0

        # Populate the UserAddress, if exists. Set the [user_group] based on the [user].
        if instance.user and instance.user.user_group:
            instance.user_group = instance.user.user_group

        instance.update_stripe()

    def post_save(sender, instance, created, *args, **kwargs):
        """Post save signal for creating a new Lead when a new location is added."""
        if created and instance.user:
            # Create a Lead for New Location
            from crm.utils import LeadUtils

            try:
                lead = LeadUtils.create_new_location(instance.user, instance)
                logger.info(f"New lead created: {lead}")
            except Exception as e:
                logger.error(f"Error creating new location lead: {e}")


pre_save.connect(UserAddress.pre_save, sender=UserAddress)
post_save.connect(UserAddress.post_save, sender=UserAddress)


class CompanyUtils:
    """This class contains utility methods for the Companies. This is used in the Customer Admin Portal."""

    @staticmethod
    def calculate_percentage_change(old_value, new_value):
        if old_value == 0:
            # Handle the case where the old value is 0 to avoid division by zero
            return "Undefined"  # Or handle it in a way that makes sense for your application
        percentage_change = ((new_value - old_value) / old_value) * 100
        return round(percentage_change)

    @staticmethod
    def get_new(search_q: str = None, owner_id: str = None):
        """Get all user addresses created in the last 30 days."""
        cutoff_date = datetime.date.today() - datetime.timedelta(days=30)
        address_q = UserAddress.objects.filter(created_on__gte=cutoff_date)
        if search_q:
            # https://docs.djangoproject.com/en/4.2/topics/db/search/
            address_q = address_q.filter(
                Q(name__icontains=search_q)
                | Q(street__icontains=search_q)
                | Q(city__icontains=search_q)
                | Q(state__icontains=search_q)
                | Q(postal_code__icontains=search_q)
            )
        if owner_id:
            address_q = address_q.filter(user_group__account_owner_id=owner_id)
        address_q = address_q.order_by("-created_on")
        return address_q

    @staticmethod
    def get_active(search_q: str = None, owner_id: str = None) -> List[UserGroup]:
        """Get all active companies.
        This returns all companies that have at least one active order in the last 30 days.
        """
        cutoff_date = datetime.date.today() - datetime.timedelta(days=30)
        # Active Companies is user group on an order within date range (or within last 30 days if no range)
        orders = Order.objects.filter(end_date__gte=cutoff_date)
        if search_q:
            orders = orders.filter(
                Q(order_group__user_address__name__icontains=search_q)
                | Q(order_group__user_address__street__icontains=search_q)
                | Q(order_group__user_address__city__icontains=search_q)
                | Q(order_group__user_address__state__icontains=search_q)
                | Q(order_group__user_address__postal_code__icontains=search_q)
            )
        if owner_id:
            orders = orders.filter(
                order_group__user_address__user_group__account_owner_id=owner_id
            )

        orders.select_related("order_group__user_address")
        orders = orders.distinct("order_group__user_address")
        orders = orders.order_by("order_group__user_address", "-end_date")
        user_addresses = []
        for order in orders:
            setattr(order.order_group.user_address, "last_order", order.end_date)
            user_addresses.append(order.order_group.user_address)
        # sort based on user_address.created_on
        user_addresses = sorted(
            user_addresses, key=lambda x: x.last_order, reverse=True
        )
        return user_addresses

    @staticmethod
    def get_churning(
        search_q: str = None,
        tab: str = None,
        owner_id: str = None,
        old_date: datetime.date = None,
        new_date: datetime.date = None,
    ) -> List[UserGroup]:
        """Get all churning companies.
        -
        if tab is "fully_churned" then Get all fully churned companies.
        Fully Churned = user group is not an active company within the date range, but was 30 days prior
        to the date range (or within last 30 days if no range)
        -
        if tab is "churning" then Get all churning companies.
        Companies that had orders in the previous 30 day period, but no orders in the last 30 day period.

        return: List of UserGroup objects
        """
        # import time

        if old_date is None:
            old_date = datetime.date.today() - datetime.timedelta(days=60)
        if new_date is None:
            new_date = datetime.date.today() - datetime.timedelta(days=30)

        # start_time = time.time()
        # Churning = sum of all order.customer total for orders within the date range for a given User Group
        # is less than the sum of the previous date range (or within last 30 days if no range)
        # ie. If I select (1) Today to last Wednesday, it will look from (2) last Wednesday to 2 Wednesdays ago
        # to compare the sums. If the sum of order totals for range 1 is less than range 2. That’s “churning”.
        #
        # Fully Churned = user group is not an active company within the date range, but was 30 days prior
        # to the date range (or within last 30 days if no range)
        orders = Order.objects.filter(end_date__gte=old_date)
        if search_q:
            orders = orders.filter(
                Q(order_group__user_address__name__icontains=search_q)
                | Q(order_group__user_address__street__icontains=search_q)
                | Q(order_group__user_address__city__icontains=search_q)
                | Q(order_group__user_address__state__icontains=search_q)
                | Q(order_group__user_address__postal_code__icontains=search_q)
            )
        if owner_id:
            orders = orders.filter(
                order_group__user_address__user_group__account_owner_id=owner_id
            )
        orders.select_related("order_group__user_address")
        orders = orders.prefetch_related("order_line_items")
        # print(orders.count())
        # step_time = time.time()
        # print(f"Query count: {step_time - start_time}")
        user_addresses_d = {}
        for order in orders:
            ugid = order.order_group.user_address_id
            if ugid not in user_addresses_d:
                user_addresses_d[ugid] = {
                    "count": 1,
                    "count_old": 0,
                    "count_new": 0,
                    "total_old": 0,
                    "total_new": 0,
                    "user_address": order.order_group.user_address,
                    "last_order": order.end_date,
                }
            user_addresses_d[ugid]["count"] += 1
            if order.end_date < new_date:
                user_addresses_d[ugid]["total_old"] += order.customer_price()
                user_addresses_d[ugid]["count_old"] += 1
            else:
                user_addresses_d[ugid]["total_new"] += order.customer_price()
                user_addresses_d[ugid]["count_new"] += 1
            if order.end_date > user_addresses_d[ugid]["last_order"]:
                user_addresses_d[ugid]["last_order"] = order.end_date
            # if len(user_addresses_d) == 10:
            #     break
        # step_time = time.time()
        # print(f"Loop orders: {step_time - start_time}")

        user_addresses = []
        for ugid, data in user_addresses_d.items():
            if data["total_old"] > data["total_new"]:
                setattr(data["user_address"], "last_order", data["last_order"])
                setattr(data["user_address"], "count_old", data["count_old"])
                setattr(data["user_address"], "count_new", data["count_new"])
                setattr(
                    data["user_address"],
                    "percent_change",
                    CompanyUtils.calculate_percentage_change(
                        data["total_old"], data["total_new"]
                    ),
                )
                setattr(
                    data["user_address"],
                    "total_spend",
                    data["total_new"] + data["total_old"],
                )
                setattr(
                    data["user_address"],
                    "change",
                    data["total_new"] - data["total_old"],
                )
                if tab == "fully_churned":
                    if data["total_new"] == 0:
                        user_addresses.append(data["user_address"])
                else:
                    user_addresses.append(data["user_address"])
        # step_time = time.time()
        # print(f"Filter churning: {step_time - start_time}")
        # Sort by change
        user_addresses = sorted(user_addresses, key=lambda x: x.change)
        # step_time = time.time()
        # print(f"Sort: {step_time - start_time}")
        return user_addresses
