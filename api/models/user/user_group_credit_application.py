from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.conf import settings

from api.models.track_data import track_data
from api.models.user.user_group import UserGroup
from api.models.order.order import Order
from common.models import BaseModel
from common.utils.get_file_path import get_file_path
from common.models.choices.approval_status import ApprovalStatus
from common.utils import customerio
import logging

logger = logging.getLogger(__name__)


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
    estimated_monthly_revenue = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
    )
    estimated_monthly_spend = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
    )
    accepts_credit_authorization = models.BooleanField(default=True)
    credit_report = models.FileField(upload_to=get_file_path, blank=True, null=True)

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


# Signal to handle post_save event for new instances with PENDING status
@receiver(post_save, sender=UserGroupCreditApplication)
def user_group_credit_application_post_save(
    sender, instance: UserGroupCreditApplication, created, **kwargs
):
    try:
        # Check if the instance is newly created and the status is PENDING
        if created and instance.status == ApprovalStatus.PENDING:
            # Retrieve the user group name
            message_data = {
                "user_group_name": instance.user_group.name,
                "requested_credit_limit": instance.requested_credit_limit,
                "estimated_monthly_revenue": instance.estimated_monthly_revenue,
                "estimated_monthly_spend": instance.estimated_monthly_spend,
                "legal_industry": None,
                "legal_address": None,
                "legal_ein": None,
                "legal_dba": None,
                "legal_structure": None,
            }
            if instance.created_by:
                message_data["user_email"] = instance.created_by.email
            else:
                message_data["user_email"] = f"N/A [application id: {instance.id}]"

            # Ensure the UserGroup model has a legal attribute
            if hasattr(instance.user_group, "legal"):
                message_data["legal_industry"] = (
                    instance.user_group.legal.industry or "N/A"
                )
                message_data["legal_address"] = (
                    f"{instance.user_group.legal.street}, {instance.user_group.legal.city}, {instance.user_group.legal.state} {instance.user_group.legal.postal_code}"
                    or "N/A"
                )
                message_data["legal_ein"] = instance.user_group.legal.tax_id or "N/A"
                message_data["legal_dba"] = (
                    instance.user_group.legal.doing_business_as or "N/A"
                )
                message_data["legal_structure"] = (
                    instance.user_group.legal.structure or "N/A"
                )

            # Trigger the Customer.io email for internal notification
            subject = f"We have received {message_data['user_group_name']}'s credit application!"
            send_to_admins = [
                "ar@downstreamsprints.atlassian.net",
                "billing@trydownstream",
            ]
            # Send email to internal team. Only on our PROD environment.
            if settings.ENVIRONMENT == "TEST":
                customerio.send_email(send_to_admins, message_data, subject, 14)

            message_data2 = {
                "user_group_name": instance.user_group.name,
                "user_first_name": instance.created_by.first_name or "Hi",
            }

            send_to = []
            if (
                hasattr(instance.user_group, "billing")
                and instance.user_group.billing.email
            ):
                send_to.append(
                    (instance.user_group.billing.email, instance.created_by.first_name)
                )
                if instance.created_by.email not in send_to:
                    send_to.append(
                        (instance.created_by.email, instance.created_by.first_name)
                    )
            else:
                # If the UserGroup does not have a billing email, send to all users in the UserGroup.
                send_to = [
                    (user.email, user.first_name)
                    for user in instance.user_group.users.all()
                ]

            # Trigger the Customer.io email for each user and the billing email
            subject = f"We have received {message_data2['user_group_name']}'s credit application for Downstream Marketplace!"
            for user_email, user_first_name in send_to:
                message_data2["user_first_name"] = user_first_name
                customerio.send_email([user_email], message_data2, subject, 9)
    except Exception as e:
        logger.error(
            f"user_group_credit_application_post_save: Failed to send email: [{instance.id}]-[{e}]"
        )


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
                instance.user_group.credit_line_limit = instance.requested_credit_limit
                instance.user_group.save()
                # Get any orders with CREDIT_APPLICATION_APPROVAL_PENDING status and update to next status.
                orders = Order.objects.filter(
                    order_group__user_address__user_group=instance.user_group,
                    status=Order.Status.CREDIT_APPLICATION_APPROVAL_PENDING,
                )
                for order in orders:
                    order.update_status_on_credit_application_approved()

                # SEND APPROVAL CREDIT EMAIL
                try:
                    message_data = {
                        "user_group_name": instance.user_group.name,
                        "user_group_credit_line_limit": instance.user_group.credit_line_limit,
                        "user_group_invoice_frequency": instance.user_group.invoice_frequency,
                        "user_group_net_terms": instance.user_group.net_terms,
                    }
                    send_to = []
                    if (
                        hasattr(instance.user_group, "billing")
                        and instance.user_group.billing.email
                    ):
                        send_to.append(
                            (
                                instance.user_group.billing.email,
                                instance.created_by.first_name,
                            )
                        )
                        if instance.created_by.email not in send_to:
                            send_to.append(
                                (
                                    instance.created_by.email,
                                    instance.created_by.first_name,
                                )
                            )
                    else:
                        # If the UserGroup does not have a billing email, send to all users in the UserGroup.
                        send_to = [
                            (user.email, user.first_name)
                            for user in instance.user_group.users.all()
                        ]

                    # Trigger the Customer.io email
                    subject = f"🎉🎉🎉 {message_data['user_group_name']} has been approved for credit with Downstream Marketplace!"
                    for user_email, user_first_name in send_to:
                        message_data["user_first_name"] = user_first_name
                        customerio.send_email([user_email], message_data, subject, 10)

                except Exception as e:
                    logger.error(
                        f"user_group_credit_application_pre_save: Failed to send email: [{instance.id}]-[{e}]"
                    )

            if instance.status == ApprovalStatus.DECLINED:
                # Only update UserGoup credit limit if there are no previously approved credit applications.
                credit_application = instance.user_group.credit_applications.filter(
                    status=ApprovalStatus.APPROVED
                )
                if not credit_application.exists():
                    # If the application is declined, set the credit limit to 0.
                    instance.user_group.credit_line_limit = 0
                    instance.user_group.save()

                # Get any orders with CREDIT_APPLICATION_APPROVAL_PENDING status and update to next status.
                orders = Order.objects.filter(
                    order_group__user_address__user_group=instance.user_group,
                    status=Order.Status.CREDIT_APPLICATION_APPROVAL_PENDING,
                )
                for order in orders:
                    order.update_status_on_credit_application_declined()

                # SEMD CREDIT DECLINED EMAIL
                try:
                    message_data = {
                        "user_group_name": instance.user_group.name,
                        "user_group_credit_line_limit": instance.user_group.credit_line_limit,
                    }
                    send_to = []
                    if (
                        hasattr(instance.user_group, "billing")
                        and instance.user_group.billing.email
                    ):
                        send_to.append(
                            (
                                instance.user_group.billing.email,
                                instance.created_by.first_name,
                            )
                        )
                        if instance.created_by.email not in send_to:
                            send_to.append(
                                (
                                    instance.created_by.email,
                                    instance.created_by.first_name,
                                )
                            )
                    else:
                        # If the UserGroup does not have a billing email, send to all users in the UserGroup.
                        send_to = [
                            (user.email, user.first_name)
                            for user in instance.user_group.users.all()
                        ]

                    # Trigger the Customer.io email
                    subject = f"{message_data['user_group_name']}'s credit application decision for Downstream Marketplace"
                    for user_email, user_first_name in send_to:
                        message_data["user_first_name"] = user_first_name
                        customerio.send_email([user_email], message_data, subject, 11)

                except Exception as e:
                    logger.error(
                        f"user_group_credit_application_pre_save: Failed to send email: [{instance.id}]-[{e}]"
                    )
