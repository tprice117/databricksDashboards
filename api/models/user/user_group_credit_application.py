from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.conf import settings

from api.models.track_data import track_data
from api.models.user.user_group import UserGroup
from api.models.user.user import User
from api.models.order.order import Order
from common.models import BaseModel
from common.utils.get_file_path import get_file_path
from common.models.choices.approval_status import ApprovalStatus
import requests
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


# TRIGGER CUSTOMERIO EMAILS
def trigger_customerio_email(
    transactional_message_id,
    user_group_name,
    user_first_name=None,
    to_user_email=None,
    user_group_credit_line_limit=None,
    user_group_invoice_frequency=None,
    user_group_net_terms=None,
    legal_industry=None,
    legal_address=None,
    created_by_user=None,
    created_by_email=None,
    legal_ein=None,
    legal_dba=None,
    legal_structure=None,
):
    url = "https://api.customer.io/v1/send/email"
    headers = {
        "Authorization": f"Bearer {settings.CUSTOMER_IO_API_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "transactional_message_id": transactional_message_id,
        "message_data": {
            "user_group_name": user_group_name,
            "user_first_name": user_first_name,
            "user_group_credit_line_limit": user_group_credit_line_limit,
            "user_group_invoice_frequency": user_group_invoice_frequency,
            "user_group_net_terms": user_group_net_terms,
            "legal_industry": legal_industry,
            "legal_address": legal_address,
            "created_by_user": created_by_user,
            "user_email": created_by_email,
            "legal_ein": legal_ein,
            "legal_dba": legal_dba,
            "legal_structure": legal_structure,
        },
        "identifiers": {
            "id": str(created_by_user),
        },
        "to": to_user_email,
    }

    # json_data = json.dumps(data, cls=DecimalEncoder)
    response = requests.post(url, json=data, headers=headers)

    if response.status_code == 200:
        print("Email sent successfully.")
    else:
        print(f"Failed to send email: {response.status_code} - {response.text}")


# Signal to handle post_save event for new instances with PENDING status
@receiver(post_save, sender=UserGroupCreditApplication)
def user_group_credit_application_post_save(
    sender, instance: UserGroupCreditApplication, created, **kwargs
):
    try:
        # Check if the instance is newly created and the status is PENDING
        if created and instance.status == ApprovalStatus.PENDING:
            # Retrieve the user group name
            user_group_name = instance.user_group.name
            if instance.created_by:
                created_by_email = instance.created_by.email
            else:
                created_by_email = f"N/A [id: {instance.id}]"

            # Ensure the UserGroup model has a legal attribute
            if hasattr(instance.user_group, "legal"):
                legal_industry = instance.user_group.legal.industry or "N/A"
                legal_address = (
                    f"{instance.user_group.legal.street}, {instance.user_group.legal.city}, {instance.user_group.legal.state} {instance.user_group.legal.postal_code}"
                    or "N/A"
                )
                legal_ein = instance.user_group.legal.tax_id or "N/A"
                legal_dba = instance.user_group.legal.doing_business_as or "N/A"
                legal_structure = instance.user_group.legal.structure or "N/A"
            else:
                legal_industry = legal_address = legal_ein = legal_dba = (
                    legal_structure
                ) = None

            # Trigger the Customer.io email for internal notification
            trigger_customerio_email(
                transactional_message_id="14",
                user_group_name=user_group_name,
                legal_industry=legal_industry,
                legal_address=legal_address,
                legal_ein=legal_ein,
                legal_dba=legal_dba,
                legal_structure=legal_structure,
                user_email=created_by_email,
                to_user_email="ar@downstreamsprints.atlassian.net",
            )

            send_to = []
            if (
                hasattr(instance.user_group, "billing")
                and instance.user_group.billing.email
            ):
                send_to.append(instance.user_group.billing.email)
            else:
                # If the UserGroup does not have a billing email, send to all users in the UserGroup.
                send_to = [user.email for user in instance.user_group.users.all()]

            user_group_name = instance.user_group.name
            user_first_name = ""  # user_dict["user_first_name"]
            to_user_email = ""  # user_dict["to_user_email"]

            # Trigger the Customer.io email for each user and the billing email
            trigger_customerio_email(
                transactional_message_id="9",
                user_group_name=instance.user_group.name,
                user_first_name=user_first_name,
                to_user_email=to_user_email,
            )
    except Exception as e:
        logger.error(
            f"user_group_credit_application_post_save: Failed to send email: {e}"
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
                # INSERT APPROVAL CREDIT EMAIL HERE
                user_group_name = instance.user_group.name
                user_group_credit_line_limit = (
                    str(instance.user_group.credit_line_limit),
                )
                user_group_invoice_frequency = (instance.user_group.invoice_frequency,)
                user_group_net_terms = instance.user_group.net_terms
                user_dicts = [
                    {
                        "user_group_name": user_group_name,
                        "user_first_name": user.first_name,
                        "user_id": user.id,
                        "to_user_email": user.email,
                    }
                    for user in instance.user_group.users.all()
                ]

                # Add the billing email to the list
                user_dicts.append(
                    {
                        "user_group_name": user_group_name,
                        "user_first_name": user_group_name,  # Assuming no first name for billing email
                        "user_id": instance.user_group.billing.id,  # Assuming no user ID for billing email
                        "to_user_email": instance.user_group.billing.email,
                    }
                )

                # Loop through each dictionary in the list
                for user_dict in user_dicts:
                    user_group_name = user_dict["user_group_name"]
                    user_first_name = user_dict["user_first_name"]
                    to_user_email = user_dict["to_user_email"]

                    # Trigger the Customer.io email for each user
                    trigger_customerio_email(
                        transactional_message_id="10",
                        user_group_name=user_group_name,
                        user_group_credit_line_limit=user_group_credit_line_limit,
                        user_group_invoice_frequency=user_group_invoice_frequency,
                        user_group_net_terms=user_group_net_terms,
                        user_first_name=user_first_name,
                        to_user_email=to_user_email,
                    )

                # Get any orders with CREDIT_APPLICATION_APPROVAL_PENDING status and update to next status.
                orders = Order.objects.filter(
                    order_group__user_address__user_group=instance.user_group,
                    status=Order.Status.CREDIT_APPLICATION_APPROVAL_PENDING,
                )
                for order in orders:
                    order.update_status_on_credit_application_approved()
            if instance.status == ApprovalStatus.DECLINED:
                # Only update UserGoup credit limit if there are no previously approved credit applications.
                credit_application = instance.user_group.credit_applications.filter(
                    status=ApprovalStatus.APPROVED
                )
                if not credit_application.exists():
                    # If the application is declined, set the credit limit to 0.
                    instance.user_group.credit_line_limit = 0
                    instance.user_group.save()
                    # INSERT CREDIT DECLINED EMAIL HERE
                    user_group_name = (instance.user_group.name,)
                    user_dicts = [
                        {
                            "user_group_name": user_group_name,
                            "user_first_name": user.first_name,
                            "user_id": user.id,
                            "to_user_email": user.email,
                        }
                        for user in instance.user_group.users.all()
                    ]

                # Add the billing email to the list
                user_dicts.append(
                    {
                        "user_group_name": user_group_name,
                        "user_first_name": user_group_name,  # Assuming no first name for billing email
                        "user_id": instance.user_group.billing.id,  # Assuming no user ID for billing email
                        "to_user_email": instance.user_group.billing.email,
                    }
                )

                # Loop through each dictionary in the list
                for user_dict in user_dicts:
                    user_group_name = user_dict["user_group_name"]
                    user_first_name = user_dict["user_first_name"]
                    to_user_email = user_dict["to_user_email"]

                    # Trigger the Customer.io email for each user
                    trigger_customerio_email(
                        transactional_message_id="11",
                        user_group_name=user_group_name,
                        user_first_name=user_first_name,
                        to_user_email=to_user_email,
                    )
                # Get any orders with CREDIT_APPLICATION_APPROVAL_PENDING status and update to next status.
                orders = Order.objects.filter(
                    order_group__user_address__user_group=instance.user_group,
                    status=Order.Status.CREDIT_APPLICATION_APPROVAL_PENDING,
                )
                for order in orders:
                    order.update_status_on_credit_application_declined()
