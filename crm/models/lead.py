from django.db import models
from django.forms import ValidationError
from django.utils.translation import gettext_lazy as _

from api.models import User, UserAddress, OrderGroup
from common.models import BaseModel
from django.utils import timezone


def get_default_est_conversion_date():
    """Return the default estimated conversion date. (7 days from current date)"""
    return timezone.now().date() + timezone.timedelta(days=7)


class Lead(BaseModel):
    class Status(models.TextChoices):
        """
        Lead.Status is an enumeration of possible statuses for a lead in the CRM system.

        Attributes:
            NEW_SIGN_UP (str): Represents a new sign-up.
            NEW_LOCATION (str): Represents a new location added.
            MANUAL (str): Represents a manually created or reengaged lead.
            CONVERTED (str): Represents a converted lead.
            INTEREST (str): Represents an interested lead.
            JUNK (str): Represents a junk lead.
        """

        # Automatic Statuses
        # Creation
        SIGN_UP = "sign_up", _("New Sign Up")
        LOCATION = "location", _("New Location Added")
        MANUAL = "manual", _("Manually Created/Reengagement")
        # Conversion
        CONVERTED = "converted", _("Converted")

        # User Selectable
        INTERESTED = "interested", _("Interest Expressed/Nurturing")
        JUNK = "junk", _("Junk")

        @classmethod
        def get_ordered_choices(cls):
            """Return the Lead.Status.choices in a specific order."""
            ordered_statuses = [
                cls.SIGN_UP,
                cls.LOCATION,
                cls.MANUAL,
                cls.INTERESTED,
                cls.CONVERTED,
                cls.JUNK,
            ]
            choices_dict = dict(cls.choices)
            return [(status, choices_dict[status]) for status in ordered_statuses]

    class Type(models.TextChoices):
        """
        Lead.Type is an enumeration of possible types for a lead in the CRM system.

        Attributes:
            CUSTOMER (str): Represents a customer lead.
            SELLER (str): Represents a supplier lead.
        """

        CUSTOMER = "customer", _("Customer")
        SELLER = "seller", _("Seller")

    class LostReason(models.TextChoices):
        """
        Lead.LostReason is an enumeration of possible reasons for losing a lead in the CRM system.

        Attributes:
            DUPLICATE (str): Represents a duplicate lead.
            INVALID (str): Represents invalid contact information.
            UNQUALIFIED (str): Represents a lead that is not a buyer/decision maker.
            UNINTERESTED (str): Represents an uninterested lead.
            JUNK (str): Represents a junk/spam/bot lead.
            EXPIRED (str): Represents a lead where the conversion date has passed.
            OTHER (str): Represents any other reason for losing a lead.
        """

        DUPLICATE = "duplicate", _("Duplicate Lead")
        INVALID = "invalid", _("Invalid Contact Information")
        UNQUALIFIED = "unqualified", _("Not a Buyer/Decision Maker")
        UNINTERESTED = "uninterested", _("Uninterested")
        JUNK = "junk", _("Junk/Spam/Bot")
        EXPIRED = "expired", _("Conversion Date Passed")
        OTHER = "other", _("Other")
        __empty__ = _("N/A")

    user = models.ForeignKey(User, related_name="user_leads", on_delete=models.CASCADE)
    user_address = models.ForeignKey(
        UserAddress, on_delete=models.CASCADE, null=True, blank=True
    )
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="owner_leads",
        null=True,
        blank=True,
    )

    est_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1000.00,
        verbose_name="Estimated Value",
    )
    est_conversion_date = models.DateField(
        null=True,
        blank=True,
        default=get_default_est_conversion_date,
        verbose_name="Estimated Conversion Date",
    )

    type = models.CharField(max_length=25, choices=Type.choices, default=Type.CUSTOMER)
    status = models.CharField(
        max_length=25, choices=Status.choices, default=Status.MANUAL
    )
    lost_reason = models.CharField(
        max_length=25, choices=LostReason.choices, null=True, blank=True
    )

    def __str__(self):
        return (
            f"{self.user} - {self.user_address} - {self.status}"
            if self.user_address
            else f"{self.user} - {self.status}"
        )

    def clean(self):
        if self.user_address:
            # Clean the User Address
            available_user_addresses = UserAddress.objects.for_user(
                self.user
            ).values_list("id", flat=True)
            if self.user_address.id not in available_user_addresses:
                raise ValidationError(_("UserAddress is not associated with the User."))
        else:
            # UserAddress is required for an interested lead
            if self.status == Lead.Status.INTERESTED:
                raise ValidationError(
                    _("UserAddress is required for an interested lead.")
                )

        # Clean the Lost Reason
        if self.status == Lead.Status.JUNK and not self.lost_reason:
            raise ValidationError(_("Lost Reason is required for a junk lead."))

        return super().clean()

    def save(self, *args, **kwargs):
        if self._state.adding:
            # New Leads should automatically set status
            if not self.user_address:
                # New User Sign Up
                self.status = Lead.Status.SIGN_UP
            elif not OrderGroup.objects.filter(user_address=self.user_address).exists():
                # New Location Added
                self.status = Lead.Status.LOCATION
            else:
                # Default to Manual
                self.status = Lead.Status.MANUAL

        self.update_conversion_status()

        return super().save(*args, **kwargs)

    def update_conversion_status(self, today=timezone.now().date()):
        """Logic to update lead statuses based on if conversion date has passed."""
        if (
            not self.lost_reason
            and self.status != Lead.Status.CONVERTED
            and self.est_conversion_date < today
        ):
            # Conversion Date has passed
            self.lost_reason = Lead.LostReason.EXPIRED
        elif (
            self.lost_reason == Lead.LostReason.EXPIRED
            and self.est_conversion_date >= today
        ):
            # Lost Reason should not be expired if conversion date has not passed
            self.lost_reason = None
            if self.status == Lead.Status.JUNK:
                self.status = Lead.Status.MANUAL

        if (
            self.lost_reason == Lead.LostReason.EXPIRED
            and self.status != Lead.Status.JUNK
        ):
            # Status should be junk if lost reason is expired
            self.status = Lead.Status.JUNK


class UserSelectableLeadStatus(models.TextChoices):
    """
    UserSelectableLeadStatus is an enumeration of lead statuses that a user can select.
    If you want the user to be able to add more statuses, add them here.

    Attributes:
        INTERESTED: Represents a lead that has shown interest.
        JUNK: Represents a lead that is considered junk.
    """

    INTERESTED = Lead.Status.INTERESTED
    JUNK = Lead.Status.JUNK
