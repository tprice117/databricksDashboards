import mailchimp_transactional as MailchimpTransactional
from django.conf import settings
from django.db import models
from django.db.models.signals import post_delete
from intercom.client import Client

from api.models.user.user_group import UserGroup
from api.utils.auth0 import create_user, delete_user, get_user_from_email, invite_user
from common.models import BaseModel

mailchimp = MailchimpTransactional.Client("md-U2XLzaCVVE24xw3tMYOw9w")


class User(BaseModel):
    user_group = models.ForeignKey(UserGroup, models.CASCADE, blank=True, null=True)
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
                                "from_email": "noreply@trydownstream.io",
                                "to": [{"email": "sales@trydownstream.io"}],
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
                except:
                    print("An exception occurred.")

        super(User, self).save(*args, **kwargs)

    def post_delete(sender, instance, **kwargs):
        # Delete auth0 user.
        try:
            delete_user(instance.user_id)
        except Exception as e:
            print("this didn't work")
            print(e)
            pass

        # TODO: Delete mailchimp user.

        # Delete intercom user.
        try:
            intercom = Client(
                personal_access_token="dG9rOjVlZDVhNWRjXzZhOWNfNGYwYl9hN2MyX2MzZmYzNzBmZDhkNDoxOjA="
            )
            contact = intercom.leads.find(id=instance.intercom_id)
            intercom.leads.delete(contact)
        except Exception as e:
            print("something went wrong with intercom")
            print(e)
            pass


post_delete.connect(User.post_delete, sender=User)
