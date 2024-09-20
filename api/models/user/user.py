import logging
import threading
import uuid
import datetime
from typing import List

import mailchimp_transactional as MailchimpTransactional
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from django.db.models import Q
from django.utils import timezone

from api.models.track_data import track_data
from api.models.user.user_group import UserGroup
from api.models.order.order import Order
from api.utils.auth0 import create_user, delete_user, get_user_from_email, invite_user
from chat.models.conversation import Conversation
from chat.models.conversation_user_last_viewed import ConversationUserLastViewed
from common.models.choices.user_type import UserType
from communications.intercom.intercom import Intercom
from notifications.utils.internal_email import send_email_on_new_signup

logger = logging.getLogger(__name__)

mailchimp = MailchimpTransactional.Client(settings.MAILCHIMP_API_KEY)


@track_data(
    "phone",
    "email",
    "first_name",
    "last_name",
    "is_archived",
    "salesforce_contact_id",
    "salesforce_seller_location_id",
    "terms_accepted",
)
class User(AbstractUser):
    class ApolloStage(models.TextChoices):
        CREATED = "CREATED", "User Created"
        ACTIVE = "ACTIVE", "Active User"
        CHURNED = "CHURNED", "Churned User"
        DEAD = "DEAD", "Dead Opportunity"

    def get_file_path(instance, filename):
        ext = filename.split(".")[-1]
        filename = "%s.%s" % (uuid.uuid4(), ext)
        return filename

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    user_group = models.ForeignKey(
        UserGroup,
        models.CASCADE,
        related_name="users",
        blank=True,
        null=True,
    )
    user_id = models.CharField(max_length=255, blank=True)
    type = models.CharField(
        max_length=255,
        choices=UserType.choices,
        default=UserType.ADMIN,
    )
    mailchip_id = models.CharField(max_length=255, blank=True, null=True)
    intercom_id = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=40, blank=True, null=True)
    email = models.CharField(max_length=255, unique=True)
    photo = models.ImageField(upload_to=get_file_path, blank=True, null=True)
    photo_url = models.TextField(blank=True, null=True)
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    device_token = models.CharField(max_length=255, blank=True, null=True)
    is_admin = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    salesforce_contact_id = models.CharField(max_length=255, blank=True, null=True)
    salesforce_seller_location_id = models.CharField(
        max_length=255, blank=True, null=True
    )
    terms_accepted = models.DateTimeField(blank=True, null=True)
    # This is used in the Auth0 login process to redirect the user to a specific page after login.
    # THis is helpful in the account creation process to redirect the user to the correct
    # page after login (supplier, customer webapp).
    redirect_url = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="URL to redirect to after Auth0 login (defaults to webapp settings.BASE_URL).",
    )
    # Apollo
    apollo_user_id = models.CharField(max_length=128, blank=True, null=True)
    apollo_id = models.CharField(max_length=128, blank=True, null=True)
    # Stage is used to track the user in Apollo.
    stage = models.CharField(
        max_length=20,
        choices=ApolloStage.choices,
        blank=True,
        null=True,
    )

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        name = self.first_name or self.last_name
        if self.first_name and self.last_name:
            name = self.first_name + " " + self.last_name
        return name

    def save(self, *args, **kwargs):
        if not self.user_id:
            # Create or attach to Auth0 user.
            user_id = get_user_from_email(self.email)

            if user_id:
                # User already exists in Auth0.
                self.user_id = user_id
                created_by_downstream_team = False
            else:
                # Create user in Auth0.
                self.user_id = create_user(self.email)
                created_by_downstream_team = True

            # Send invite email.
            if created_by_downstream_team:
                invite_user(self)

            # Send email to internal team. Only on our PROD environment.
            if settings.ENVIRONMENT == "TEST":
                send_email_on_new_signup(
                    self.email, created_by_downstream_team=created_by_downstream_team
                )

        # Create new Intercom account if no intercom_id exists
        if not self.intercom_id:
            # Create Intercom contact synchronously, so that the user has a good intercom_id.
            contact = self.intercom_sync(save_data=False, create_company=False)
            if contact:
                self.intercom_id = contact["id"]
                if self.user_group:
                    # Update Intercom contact asynchronously to speed up save.
                    # Note: This is done asynchronously because it is not critical.
                    p = threading.Thread(target=self.intercom_sync)
                    p.start()
        else:
            # Update Intercom contact asynchronously to speed up save.
            # Note: This is done asynchronously because it is not critical.
            p = threading.Thread(target=self.intercom_sync)
            p.start()

        super(User, self).save(*args, **kwargs)

    def post_delete(sender, instance, **kwargs):
        # Delete auth0 user.
        try:
            delete_user(instance.user_id)
        except Exception as e:
            logger.error(f"User.post_delete: [{e}]", exc_info=e)

        # TODO: Delete mailchimp user.

        # Delete intercom user.
        try:
            Intercom.Contact.delete(instance.intercom_id)
        except Exception as e:
            logger.error(f"User.post_delete: [{e}]", exc_info=e)

    def intercom_sync(self, save_data=True, create_company=True):
        """Synchronizes the user's data with Intercom.

        Args:
            create_company (bool, optional): Indicates whether to create a company in Intercom if it doesn't exist. Defaults to True.

        Returns:
            dict: The ContactType from Intercom.
        """
        try:
            photo_url = None
            if self.photo:
                photo_url = self.photo.url
            if self.intercom_id:
                contact = Intercom.Contact.get(self.intercom_id)
                if contact:
                    if (
                        contact["name"] != self.full_name
                        or contact["email"] != self.email
                        or contact["phone"] != self.phone
                        or contact["avatar"] != photo_url
                    ):
                        Intercom.Contact.update(
                            self.intercom_id,
                            str(self.id),
                            self.email,
                            name=self.full_name,
                            phone=self.phone,
                            avatar=photo_url,
                        )
            else:
                contact = Intercom.Contact.create(
                    str(self.id),
                    self.email,
                    name=self.full_name,
                    phone=self.phone,
                    avatar=photo_url,
                )
                if contact and save_data:
                    User.objects.filter(id=self.id).update(intercom_id=contact["id"])
            if create_company and self.user_group and contact:
                # Update or create Company in Intercom
                company = Intercom.Company.update_or_create(
                    str(self.user_group.id),
                    self.user_group.name,
                    custom_attributes=self.user_group.intercom_custom_attributes,
                )
                if company:
                    # Attach user to company
                    Intercom.Contact.attach_user(company["id"], self.intercom_id)
                    if self.user_group.intercom_id != company["id"] and save_data:
                        UserGroup.objects.filter(id=self.user_group.id).update(
                            intercom_id=company["id"]
                        )
            return contact
        except Exception as e:
            logger.error(f"User.intercom_sync: [{e}]", exc_info=e)
            return None

    def unread_conversations_count(self):
        return self.unread_conversations().count()

    def unread_conversations(self):
        """
        Get Conversations related to this User.

        a) If the user is_staff, they see all Conversations.
        b) If the user is not_staff and their UserGroup has a Seller,
           they see all Conversations for Bookings for which their Seller
           (OrderGroup.SellerProductSellerLocation.SellerLocation.Seller)
           is the Seller.
        c) If the user is not_staff and their UserGroup does not have a Seller,
           no Conversations are returned.
        """
        # Get ConversationUserLastViewed objects for this User.
        conversation_user_last_vieweds = ConversationUserLastViewed.objects.filter(
            user=self
        )

        if self.is_staff:
            # Get all Conversations where User doesn't have a ConversationUserLastViewed
            # or the ConversationUserLastViewed.updated_on is less than the most recent
            # Message.created_on for the Conversation.
            return Conversation.objects.filter(
                messages__created_on__gt=models.Subquery(
                    conversation_user_last_vieweds.filter(
                        conversation=models.OuterRef("pk")
                    )
                    .order_by("-updated_on")
                    .values("updated_on")[:1]
                )
            ).distinct()
        elif self.user_group and self.user_group.seller:
            # Get all Conversations for the UserGroup's Seller.
            # order_groups = OrderGroup.objects.filter(
            #     seller_product_seller_location__seller_location__seller=self.user_group.seller
            # )

            # Get all Conversations for the OrderGroups. Walk the reverse relationship
            # from User to OrderGroup.
            seller_locations = self.user_group.seller.seller_locations.all()

            # Get SellerProductSellerLocations for the SellerLocations.
            seller_product_seller_locations = []
            for seller_location in seller_locations:
                seller_product_seller_locations.extend(
                    seller_location.seller_product_seller_locations.all()
                )

            # Get OrderGroups for the SellerProductSellerLocations.
            order_groups = []
            for seller_product_seller_location in seller_product_seller_locations:
                order_groups.extend(seller_product_seller_location.order_groups.all())

            # Select the Conversation from the OrderGroups.
            order_group_conversations = []
            for order_group in order_groups:
                order_group_conversations.append(order_group.conversation)

            return order_group_conversations.filter(
                messages__created_on__gt=models.Subquery(
                    conversation_user_last_vieweds.filter(
                        conversation=models.OuterRef("pk")
                    )
                    .order_by("-updated_on")
                    .values("updated_on")[:1]
                )
            ).distinct()
        else:
            return Conversation.objects.none()

    def get_allowed_user_types(self):
        user_types = UserType.choices
        if not self.is_staff:
            if self.type == UserType.BILLING:
                user_types = [
                    (UserType.BILLING, UserType.BILLING),
                    (UserType.MEMBER, UserType.MEMBER),
                ]
            elif self.type == UserType.MEMBER:
                user_types = [
                    (UserType.MEMBER, UserType.MEMBER),
                ]
        return user_types


post_delete.connect(User.post_delete, sender=User)


@receiver(pre_save, sender=User)
def user_pre_save(sender, instance: User, *args, **kwargs):
    db_instance = User.objects.filter(id=instance.id).first()

    if not db_instance:
        # User is being created.
        instance.username = instance.email
        instance.password = str(uuid.uuid4())

        if not instance.type:
            instance.type = UserType.ADMIN


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
    def get_new(search_q: str = None):
        """Get all users created in the last 30 days."""
        cutoff_time = timezone.now() - datetime.timedelta(days=30)
        users_q = User.objects.filter(date_joined__gte=cutoff_time)
        if search_q:
            # https://docs.djangoproject.com/en/4.2/topics/db/search/
            users_q = users_q.filter(
                Q(first_name__icontains=search_q)
                | Q(last_name__icontains=search_q)
                | Q(email__icontains=search_q)
            )
        users_q = users_q.order_by("-date_joined")
        return users_q

    @staticmethod
    def get_loggedin(search_q: str = None):
        """Get all users who have logged in, in the last 30 days."""
        cutoff_time = timezone.now() - datetime.timedelta(days=30)
        users_q = User.objects.filter(last_login__gte=cutoff_time)
        if search_q:
            # https://docs.djangoproject.com/en/4.2/topics/db/search/
            users_q = users_q.filter(
                Q(first_name__icontains=search_q)
                | Q(last_name__icontains=search_q)
                | Q(email__icontains=search_q)
            )
        users_q = users_q.order_by("-date_joined")
        return users_q

    @staticmethod
    def get_active(search_q: str = None) -> List[UserGroup]:
        """Get all active buyers.
        This returns all users who have an order in the last 30 days.
        """
        cutoff_time = timezone.now() - datetime.timedelta(days=30)
        # Active Companies is user group on an order within date range (or within last 30 days if no range)
        orders = Order.objects.filter(end_date__gte=cutoff_time)
        if search_q:
            orders = orders.filter(
                Q(order_group__user__first_name__icontains=search_q)
                | Q(order_group__user__last_name__icontains=search_q)
                | Q(order_group__user__email__icontains=search_q)
            )

        orders.select_related("order_group__user")
        orders = orders.distinct("order_group__user")
        orders = orders.order_by("order_group__user", "-end_date")
        users = []
        for order in orders:
            setattr(order.order_group.user, "last_order", order.end_date)
            users.append(order.order_group.user)
        # sort based on users.created_on
        users = sorted(users, key=lambda x: x.last_order, reverse=True)
        return users

    @staticmethod
    def get_churning(
        search_q: str = None,
        tab: str = None,
        old_date: datetime.date = None,
        new_date: datetime.date = None,
    ) -> List[User]:
        """Get all churning buyers.
        -
        if tab is "fully_churned" then Get all fully churned buyers.
        Fully Churned = user group is not an active company within the date range, but was 30 days prior
        to the date range (or within last 30 days if no range)
        -
        if tab is "churning" then Get all churning buyers.
        Buyers that had orders in the previous 30 day period, but no orders in the last 30 day period.

        return: List of User objects
        """
        import time

        if old_date is None:
            old_date = datetime.date.today() - datetime.timedelta(days=60)
        if new_date is None:
            new_date = datetime.date.today() - datetime.timedelta(days=30)

        start_time = time.time()
        orders = Order.objects.filter(end_date__gte=old_date)
        if search_q:
            orders = orders.filter(
                Q(order_group__user__first_name__icontains=search_q)
                | Q(order_group__user__last_name__icontains=search_q)
                | Q(order_group__user__email__icontains=search_q)
            )
        orders.select_related("order_group__user")
        orders = orders.prefetch_related("order_line_items")
        print(orders.count())
        step_time = time.time()
        print(f"Query count: {step_time - start_time}")
        users_d = {}
        for order in orders:
            ugid = order.order_group.user_id
            if ugid not in users_d:
                users_d[ugid] = {
                    "count": 1,
                    "count_old": 0,
                    "count_new": 0,
                    "total_old": 0,
                    "total_new": 0,
                    "user": order.order_group.user,
                    "last_order": order.end_date,
                }
            users_d[ugid]["count"] += 1
            if order.end_date < new_date:
                users_d[ugid]["total_old"] += order.customer_price()
                users_d[ugid]["count_old"] += 1
            else:
                users_d[ugid]["total_new"] += order.customer_price()
                users_d[ugid]["count_new"] += 1
            if order.end_date > users_d[ugid]["last_order"]:
                users_d[ugid]["last_order"] = order.end_date
            # if len(users_d) == 10:
            #     break
        step_time = time.time()
        print(f"Loop orders: {step_time - start_time}")

        users = []
        for ugid, data in users_d.items():
            if data["total_old"] > data["total_new"]:
                setattr(data["user"], "last_order", data["last_order"])
                setattr(data["user"], "count_old", data["count_old"])
                setattr(data["user"], "count_new", data["count_new"])
                setattr(
                    data["user"],
                    "percent_change",
                    CompanyUtils.calculate_percentage_change(
                        data["total_old"], data["total_new"]
                    ),
                )
                setattr(
                    data["user"],
                    "total_spend",
                    data["total_new"] + data["total_old"],
                )
                setattr(
                    data["user"],
                    "change",
                    data["total_new"] - data["total_old"],
                )
                if tab == "fully_churned":
                    if data["total_new"] == 0:
                        users.append(data["user"])
                else:
                    users.append(data["user"])
        step_time = time.time()
        print(f"Filter churning: {step_time - start_time}")
        # Sort by change
        users = sorted(users, key=lambda x: x.change)
        step_time = time.time()
        print(f"Sort: {step_time - start_time}")
        return users
