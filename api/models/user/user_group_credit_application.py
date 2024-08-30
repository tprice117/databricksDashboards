from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver

from api.models.track_data import track_data
from api.models.user.user_group import UserGroup
from api.models.order.order import Order
from common.models import BaseModel
from common.models.choices.approval_status import ApprovalStatus


@track_data("status")
class UserGroupCreditApplication(BaseModel):
    user_group = models.ForeignKey(
        UserGroup,
        models.CASCADE,
        related_name="credit_applications",
    )
    requested_credit_limit = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
    )
    status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
    )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def clean(self):
        self.clean_fields()

        # Check if there is an existing pending application for this user group.
        # If there is, raise a validation error to prevent multiple pending
        # applications.
        if self.status == ApprovalStatus.PENDING:
            existing_application = UserGroupCreditApplication.objects.filter(
                user_group=self.user_group, status=ApprovalStatus.PENDING
            ).exists()
            if existing_application:
                raise ValidationError(
                    "A pending credit application already exists for this user group."
                )
        return self


@receiver(pre_save, sender=UserGroupCreditApplication)
def user_group_credit_application_pre_save(
    sender,
    instance: UserGroupCreditApplication,
    *args,
    **kwargs,
):
    if instance.has_changed("status"):
        old_status = instance.old_value("status")

        # If old status is APPROVED or DECLINED, throw an error.
        if old_status in [
            ApprovalStatus.APPROVED,
            ApprovalStatus.DECLINED,
        ]:
            raise ValidationError(
                "Cannot change status of an approved or declined credit application."
            )
        else:
            # If old status is PENDING and new status is APPROVED,
            # update the user group's credit limit.
            if instance.status == ApprovalStatus.APPROVED:
                instance.user_group.credit_limit = instance.requested_credit_limit
                instance.user_group.save()
                # Get any orders with CREDIT_APPLICATION_APPROVAL_PENDING status and update to next status.
                orders = Order.objects.filter(
                    order_group__user_group=instance.user_group,
                    status=Order.Status.CREDIT_APPLICATION_APPROVAL_PENDING,
                )
                for order in orders:
                    order.update_status_on_credit_application_approved()
