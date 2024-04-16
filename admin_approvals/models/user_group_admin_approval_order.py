from django.utils import timezone
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
import logging

from api.models.order.order import Order
from api.models.track_data import track_data
from common.models import BaseModel

logger = logging.getLogger(__name__)


@track_data("status")
class UserGroupAdminApprovalOrder(BaseModel):
    """
    When the UserGroupPolicyPurchaseApproval or UserGroupPolicyMonthlyLimit policy dictates
    (either the Order exceeds the UserGroupPolicyPurchaseApproval amount or the Order causes
    the UserGroupPolicyMonthlyLimit to exceed the allotted amount), any Order created by
    BillingManager or Member users will create an instance of this object. After Admin approval,
    the Order will be submitted.
    """

    class ApprovalStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACCEPTED = "ACCEPTED", "Accepted"
        DECLINED = "DECLINED", "Declined"

    order = models.OneToOneField(
        Order,
        models.CASCADE,
        related_name="user_group_admin_approval_order",
    )
    status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
    )

    def __str__(self):
        return f"{self.order.id}"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        # Only allow changes to be made if the Status == PENDING.
        if self.old_value("status") == self.ApprovalStatus.PENDING:
            super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Order Approval"
        verbose_name_plural = "Order Approvals"


@receiver(pre_save, sender=UserGroupAdminApprovalOrder)
def pre_save_user_group_admin_approval_order(
    sender, instance: UserGroupAdminApprovalOrder, **kwargs
):
    old_status = instance.old_value("status")

    if old_status == UserGroupAdminApprovalOrder.ApprovalStatus.PENDING:
        if instance.status == UserGroupAdminApprovalOrder.ApprovalStatus.ACCEPTED:
            # If Status changes from PENDING to APPROVED, populate the Order.SubmittedOn
            # field with the current date time. This indicates the Order is submitted.
            instance.order.submitted_on = timezone.now()
            instance.order.save()
        elif old_status == UserGroupAdminApprovalOrder.ApprovalStatus.DECLINED:
            # If the Status changes from PENDING to DECLINED, update Status, then do nothing else.
            logger.warning(
                f"Approval for order {instance.order.id} has been declined. No further action will be taken."
            )
