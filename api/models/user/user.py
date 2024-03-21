import mailchimp_transactional as MailchimpTransactional
from django.conf import settings
from django.db import models
from django.db.models.signals import post_delete
import threading
import logging
from communications.intercom.intercom import Intercom
from api.models.track_data import track_data

from api.models.user.user_group import UserGroup
from api.utils.auth0 import create_user, delete_user, get_user_from_email, invite_user
from common.models import BaseModel

logger = logging.getLogger(__name__)

mailchimp = MailchimpTransactional.Client(settings.MAILCHIMP_API_KEY)


@track_data('phone', 'email', 'first_name', 'last_name', 'is_archived', 'salesforce_contact_id', 'salesforce_seller_location_id', 'terms_accepted')
class User(BaseModel):
    user_group = models.ForeignKey(
        UserGroup,
        models.CASCADE,
        related_name="users",
        blank=True,
        null=True,
    )
    user_id = models.CharField(max_length=255, blank=True)
    mailchip_id = models.CharField(max_length=255, blank=True, null=True)
    intercom_id = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=40, blank=True, null=True)
    email = models.CharField(max_length=255, unique=True)
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

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        name = self.first_name or self.last_name
        if (self.first_name and self.last_name):
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
                try:
                    mailchimp.messages.send(
                        {
                            "message": {
                                "headers": {
                                    "reply-to": self.email,
                                },
                                "from_name": "Downstream",
                                "from_email": "noreply@trydownstream.com",
                                "to": [{"email": "sales@trydownstream.com"}],
                                "subject": "New User App Signup",
                                "track_opens": True,
                                "track_clicks": True,
                                "text": "Woohoo! A new user signed up for the app. The email on their account is: ["
                                + self.email
                                + "]. This was created by: "
                                + (
                                    "[DOWNSTREAM TEAM]"
                                    if created_by_downstream_team
                                    else "[]"
                                )
                                + ".",
                            }
                        }
                    )
                except Exception as e:
                    logger.error(f"User.save: [{e}]", exc_info=e)

        # Create new Intercom account if no intercom_id exists
        if not self.intercom_id:
            # Create Intercom contact synchronously, so that the user has a good intercom_id.
            contact = self.intercom_sync(save_data=False, create_company=False)
            if contact:
                self.intercom_id = contact["id"]
                if (self.user_group):
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
        if self.intercom_id:
            contact = Intercom.Contact.get(self.intercom_id)
            if contact:
                if (contact["name"] != self.full_name or
                    contact["email"] != self.email or
                    contact["phone"] != self.phone or
                        contact["avatar"] != self.photo_url):
                    Intercom.Contact.update(self.intercom_id, str(self.id), self.email, name=self.full_name,
                                            phone=self.phone, avatar=self.photo_url)
        else:
            contact = Intercom.Contact.create(str(self.id), self.email,
                                              name=self.full_name, phone=self.phone, avatar=self.photo_url)
            if contact and save_data:
                User.objects.filter(id=self.id).update(intercom_id=contact["id"])
        if create_company and self.user_group and contact:
            # Update or create Company in Intercom
            company = Intercom.Company.update_or_create(
                str(self.user_group.id), self.user_group.name,
                custom_attributes=self.user_group.intercom_custom_attributes
            )
            if company:
                # Attach user to company
                Intercom.Contact.attach_user(company["id"], self.intercom_id)
                if self.user_group.intercom_id != company["id"] and save_data:
                    UserGroup.objects.filter(id=self.user_group.id).update(intercom_id=company["id"])
        return contact


post_delete.connect(User.post_delete, sender=User)
