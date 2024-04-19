from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver

from api.models.order.order import Order
from api.models.track_data import track_data
from common.models import BaseModel
from common.models.choices.approval_status import ApprovalStatus


@track_data("status")
class UserGroupAdminApprovalOrder(BaseModel):
    """
    When the UserGroupPolicyPurchaseApproval or UserGroupPolicyMonthlyLimit policy dictates
    (either the Order exceeds the UserGroupPolicyPurchaseApproval amount or the Order causes
    the UserGroupPolicyMonthlyLimit to exceed the allotted amount), any Order created by
    BillingManager or Member users will create an instance of this object. After Admin approval,
    the Order will be submitted.
    """

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
        self.__original_status = self.name

    # Pre/post save, check Status.
    # 1. If Status changes from PENDING to APPROVED, populate the Order.SubmittedOn field with the current date
    # time. This indicates the Order is submitted.
    # 2. If the Status changes from PENDING to DECLINED, update Status, then do nothing else. Question: do we delete Order?
    # 3. Do not allow any changes to be made if either the Status == DECLINED or Status == APPROVED.


# Pre_save reciever. If Status changes from PENDING to APPROVED, populate the Order.SubmittedOn field with the current date
# time. This indicates the Order is submitted.


@receiver(pre_save, sender=UserGroupAdminApprovalOrder)
def pre_save_user_group_admin_approval_order(
    sender, instance: UserGroupAdminApprovalOrder, **kwargs
):
    old_status: UserGroupAdminApprovalOrder.ApprovalStatus
    old_status = instance.old_value("status")

    if old_status == UserGroupAdminApprovalOrder.ApprovalStatus.ACCEPTED:
        djksld
        jakld
        ajs
