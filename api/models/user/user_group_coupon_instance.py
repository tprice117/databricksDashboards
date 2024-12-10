from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from api.models import Order
from api.models.track_data import track_data
from api.models.user.user import User
from api.models.user.user_group import UserGroup
from common.models import BaseModel
from common.models.choices.user_type import UserType
from coupons.models import Coupon
from notifications.utils.add_email_to_queue import add_email_to_queue


@track_data("owner")
class UserGroupCouponInstance(BaseModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        REDEEMED = "redeemed", "Redeemed"
        EXPIRED = "expired", "Expired"

    user_group = models.ForeignKey(
        UserGroup,
        models.CASCADE,
    )
    coupon = models.ForeignKey(
        Coupon,
        models.CASCADE,
    )
    owner = models.ForeignKey(
        User,
        models.CASCADE,
        blank=True,
        null=True,
    )
    order = models.ForeignKey(
        Order,
        models.CASCADE,
        blank=True,
        null=True,
        help_text="The order that this coupon was used on. If this is "
        "blank, the coupon has not been used yet.",
    )

    def __str__(self):
        return f"{self.user_group.name} - {self.coupon.__str__()}"

    class Meta:
        verbose_name = "Account Coupon Instance"
        verbose_name_plural = "Account Coupon Instances"

    def clean(self):
        # Ensure the owner of the coupon is part of the user group.
        if self.owner not in self.user_group.users.all():
            raise ValidationError(
                "The owner of the coupon must be part of the user group."
            )

    @property
    def redeemed(self):
        """
        The coupon is considered redeemed if it has been used on an order.
        """
        return self.order is not None

    @property
    def expired(self):
        """
        The coupon is considered expired if it is no longer valid (based on
        the coupon's valid_from and valid_to dates).
        """
        return not self.coupon.is_valid

    @property
    def status(self):
        if self.redeemed:
            return self.Status.REDEEMED
        elif self.expired:
            return self.Status.EXPIRED
        else:
            return self.Status.ACTIVE


# Signal to handle post_save event for new instances with PENDING status
@receiver(post_save, sender=UserGroupCouponInstance)
def user_group_coupon_instance_post_save(
    sender, instance: UserGroupCouponInstance, created, **kwargs
):
    if created:
        # Send email to the owner of the coupon (if non-NULL) or the
        # UserGroup Admins and BillingManagers.
        to_emails = (
            [
                instance.owner.email,
            ]
            if instance.owner
            else [
                user.email
                for user in instance.user_group.users.filter(
                    type__in=[
                        UserType.ADMIN,
                        UserType.BILLING,
                    ]
                )
            ]
        )

        add_email_to_queue(
            from_email="dispatch@trydownstream.com",
            to_emails=to_emails,
            subject=f"Downstream Coupon: {instance.coupon.text}",
            html_content=f"Hello {instance.owner.first_name},<br><br>"
            f"Your Downstream coupon has been created. "
            f"Use code <strong>{instance.coupon.code}</strong> "
            f"to redeem {instance.coupon.text}.<br><br>"
            f"Valid from: {instance.coupon.valid_from}<br>"
            f"Valid to: {instance.coupon.valid_to}<br><br>"
            f"Happy shopping!<br><br>"
            f"Downstream Team",
            reply_to="dispatch@trydownstream.com",
        )
    elif instance.has_changed("owner"):
        # If the owner of the coupon changes, send an email to the new owner.
        add_email_to_queue(
            from_email="dispatch@trydownstream.com",
            to_emails=[
                instance.owner.email,
            ],
            subject=f"Downstream Coupon: {instance.coupon.text}",
            html_content=f"Hello {instance.owner.first_name},<br><br>"
            f"{instance.old_value('owner').email} has transferred "
            f"their Downstream coupon to you. "
            f"Use code <strong>{instance.coupon.code}</strong> "
            f"to redeem {instance.coupon.text}.<br><br>"
            f"Valid from: {instance.coupon.valid_from}<br>"
            f"Valid to: {instance.coupon.valid_to}<br><br>"
            f"Happy shopping!<br><br>"
            f"Downstream Team",
            reply_to="dispatch@trydownstream.com",
        )
