import logging
import threading

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from communications.intercom.utils.utils import get_json_safe_value
from common.utils.customerio import send_event, update_person, update_company
from api.models import UserAddress, UserGroup, User, OrderGroup, Order

logger = logging.getLogger(__name__)

"""Order track fields needed for sending email notifications on Order submitted and Order status changed.
If another field needs to be tracked, go to the model class and edit the
track_data class decorator parameters.

Django Signals help: https://docs.djangoproject.com/en/5.0/topics/signals/
"""


# def get_order_status_from_choice(status: str) -> str:
#     """Get the status from Order.STATUS_CHOICES.

#     Args:
#         status (str): The db status value.

#     Returns:
#         str: The human readable status.
#     """
#     from api.models import Order

#     for choice in Order.STATUS_CHOICES:
#         if choice[0] == status:
#             return choice[1]
#     return "Unknown"


# ================================================#
# Email on Order database actions
# ================================================#


def on_order_post_save(sender, instance, created, **kwargs):
    """Sends an email on Order database actions, such as Order created, submitted or status changed
    to SCHEDULED."""

    order: Order = instance
    bcc_emails = []
    if settings.ENVIRONMENT == "TEST":
        bcc_emails.append("dispatch@trydownstream.com")
    if created is False:
        # Order updated
        error_status = "created-Order"
        order_id = get_json_safe_value(order.id)
        try:
            if order.submitted_on is not None:
                if order.old_value("submitted_on") is None:
                    # TODO: This should only send if the order is not in CREDIT_APPLICATION_APPROVAL_PENDING
                    order.send_supplier_approval_email()

                    # TODO: Switch this to the new template that is similar to the supplier approval email, do not cc dispatch.
                    # # Order submitted
                    # subject = "Thanks for your order!"
                    # html_content = render_to_string(
                    #     "notifications/emails/order_submitted.html", {"order": order}
                    # )
                    # add_email_to_queue(
                    #     from_email="dispatch@trydownstream.com",
                    #     to_emails=[order.order_group.user.email],
                    #     bcc_emails=bcc_emails,
                    #     subject=subject,
                    #     html_content=html_content,
                    #     reply_to="dispatch@trydownstream.com",
                    # )
                elif order.old_value("status") != order.status:
                    if order.status == Order.Status.SCHEDULED:
                        order.send_customer_email_when_order_scheduled()
                        order.close_admin_chat(message="Order has been scheduled.")
                    # elif (
                    #     order.status == Order.Status.CANCELLED
                    #     or order.status == Order.Status.COMPLETE
                    # ):
                    #     subject = "Your Downstream order has been completed!"
                    #     if order.status == Order.Status.CANCELLED:
                    #         subject = "Your Downstream order has been cancelled"
                    #     error_status = "updated-Order"
                    #     # Order status changed
                    #     html_content = render_to_string(
                    #         "notifications/emails/order_status_change.html",
                    #         {
                    #             "order": order,
                    #             "new_status": get_order_status_from_choice(
                    #                 order.status
                    #             ),
                    #             "previous_status": get_order_status_from_choice(
                    #                 order.old_value("status")
                    #             ),
                    #         },
                    #     )
                    #     add_email_to_queue(
                    #         from_email="dispatch@trydownstream.com",
                    #         to_emails=[order.order_group.user.email],
                    #         subject=subject,
                    #         html_content=html_content,
                    #         reply_to="dispatch@trydownstream.com",
                    #     )
        except Exception as e:
            logger.exception(f"notification: [{order_id}]-[{error_status}]-[{e}]")
    else:
        try:
            if order.submitted_on is not None:
                order.send_supplier_approval_email()
        except Exception as e:
            logger.exception(f"notification: [{order_id}]-[{error_status}]-[{e}]")


# TODO: This is being called from api.models.order.order.py pre_save to ensure line items are
# saved before this is called. This is a temporary solution until a better solution is found.
# post_save.connect(on_order_post_save, sender=Order)


@receiver(post_save, sender=UserGroup)
def on_user_group_post_save(sender, instance: UserGroup, created, *args, **kwargs):
    """Sends an event when a UserGroup is created, specifically for tracking user-related events."""

    if created:
        event_name = "user_group_created"
    else:
        event_name = "user_group_updated"

    def _send_event():
        try:
            # Add user attributes to CustomerIO
            event_data = {
                "id": str(instance.id),
                "name": instance.name,
                "pay_later": instance.pay_later,
                "industry": instance.industry,
                "autopay": instance.autopay,
                "net_terms": instance.net_terms,
                "stripe_id": instance.stripe_id,
                "credit_line_limit": instance.credit_line_limit,
                "compliance_status": instance.compliance_status,
                "tax_exempt_status": instance.tax_exempt_status,
                "RPP_COI_Exp_Date": instance.RPP_COI_Exp_Date.isoformat()
                if instance.RPP_COI_Exp_Date
                else None,
                "account_owner": instance.account_owner,
                "apollo_id": instance.apollo_id,
                "stage": instance.stage,
                "credit_limit_used": instance.credit_limit_used(),
                "lifetime_spend": instance.lifetime_spend(),
            }

            if hasattr(instance, "legal") and instance.legal:
                event_data["legal_name"] = instance.legal.name
                event_data["legal_tax_id"] = instance.legal.tax_id
                event_data["legal_accepted_net_terms"] = (
                    instance.legal.accepted_net_terms
                )
                event_data["legal_years_in_business"] = instance.legal.years_in_business
                event_data["legal_doing_business_as"] = instance.legal.doing_business_as
                event_data["legal_structure"] = instance.legal.structure
                event_data["legal_industry"] = instance.legal.industry
                event_data["legal_address"] = instance.legal.formatted_address
            if hasattr(instance, "billing") and instance.billing:
                event_data["billing_name"] = instance.billing.name
                event_data["billing_address"] = instance.billing.formatted_address
                event_data["billing_tax_id"] = instance.billing.tax_id

            if instance.seller:
                event_data["seller"] = str(instance.seller.id)
                event_data["seller_name"] = instance.seller.name
                event_data["seller_email"] = instance.seller.order_email
                event_data["seller_phone"] = instance.seller.order_phone
                event_data["seller_type"] = instance.seller.type
                event_data["seller_location_type"] = instance.seller.location_type
                event_data["seller_status"] = instance.seller.status
                event_data["seller_logo"] = (
                    instance.seller.logo.url if instance.seller.logo else None
                )
                event_data["seller_lead_time"] = instance.seller.lead_time
                event_data["seller_badge"] = instance.seller.badge
            sending_user_email = None
            if instance.updated_by:
                sending_user_email = instance.updated_by.email
            else:
                first_user = instance.users.first()
                if first_user:
                    sending_user_email = first_user.email

            if sending_user_email:
                update_company(sending_user_email, str(instance.id), event_data)
            else:
                logger.error(
                    f"on_user_group_post_save:{event_name}: [{instance.id}]-[No user to send company to]"
                )
        except Exception as e:
            logger.exception(
                f"on_user_group_post_save:{event_name}: [{instance.id}]-[{e}]"
            )

    if settings.ENVIRONMENT == "TEST":
        p = threading.Thread(target=_send_event)
        p.start()


@receiver(post_save, sender=User)
def on_user_post_save(sender, instance: User, created, **kwargs):
    """Sends an event when a User is created, specifically for tracking user-related events."""

    def _send_event():
        try:
            # Add user attributes to CustomerIO
            event_data = {
                "id": str(instance.id),
                "email": instance.email,
                "first_name": instance.first_name,
                "last_name": instance.last_name,
                "phone": instance.phone,
                "photo": instance.photo.url if instance.photo else None,
                "mailchimp_id": instance.mailchip_id,
                "user_group": str(instance.user_group.id)
                if instance.user_group
                else None,
                "type": instance.type,
                "source": instance.source,
                "is_archived": instance.is_archived,
                "intercom_id": instance.intercom_id,
                "salesforce_contact_id": instance.salesforce_contact_id,
                "salesforce_seller_location_id": instance.salesforce_seller_location_id,
                "terms_accepted": instance.terms_accepted.isoformat()
                if instance.terms_accepted
                else None,
                "redirect_url": instance.redirect_url,
                "apollo_user_id": instance.apollo_user_id,
                "apollo_id": instance.apollo_id,
                "stage": instance.stage,
                "last_active": instance.last_active.isoformat()
                if instance.last_active
                else None,
            }
            update_person(instance.email, event_data)
        except Exception as e:
            logger.exception(f"on_user_post_save: [{instance.id}]-[{e}]")

    if settings.ENVIRONMENT == "TEST":
        p = threading.Thread(target=_send_event)
        p.start()


@receiver(post_save, sender=UserAddress)
def on_user_address_post_save(sender, instance: UserAddress, created, **kwargs):
    """Sends an event when a UserAddress is created, specifically for tracking user-related events."""

    if created:
        event_name = "user_address_created"
    else:
        event_name = "user_address_updated"

    def _send_event():
        try:
            # Add user attributes to CustomerIO
            event_data = {
                "id": str(instance.id),
                "user": str(instance.user_id),
                "user_group": str(instance.user_group_id),
                "name": instance.name,
                "address": instance.formatted_address(),
                "project_id": instance.project_id,
                "street": instance.street,
                "street2": instance.street2,
                "city": instance.city,
                "state": instance.state,
                "postal_code": instance.postal_code,
                "country": instance.country,
                "latitude": str(instance.latitude),
                "longitude": str(instance.longitude),
                "access_details": instance.access_details,
                "autopay": instance.autopay,
                "is_archived": instance.is_archived,
                "allow_saturday_delivery": instance.allow_saturday_delivery,
                "allow_sunday_delivery": instance.allow_sunday_delivery,
                "tax_exempt_status": instance.tax_exempt_status,
                "user_address_type": instance.user_address_type.name
                if instance.user_address_type
                else None,
                "default_payment_method": instance.default_payment_method,
                "should_collect_taxes": instance.should_collect_taxes,
            }
            send_event(instance.user.email, event_name, event_data)
        except Exception as e:
            logger.exception(f"on_user_address_post_save: [{instance.id}]-[{e}]")

    if settings.ENVIRONMENT == "TEST":
        p = threading.Thread(target=_send_event)
        p.start()


@receiver(post_save, sender=Order)
def on_order_post_save2(sender, instance: Order, created, **kwargs):
    """Sends an event when an Order is created, specifically for tracking user-related events."""

    if created:
        event_name = "order_created"
    else:
        event_name = "order_updated"

    def _send_event():
        try:
            # Add user attributes to CustomerIO
            user_cart_count = (
                OrderGroup.objects.filter(user_id=instance.order_group.user_id)
                .filter(orders__submitted_on__isnull=True)
                .count()
            )
            user_booking_count = (
                OrderGroup.objects.filter(user_id=instance.order_group.user_id)
                .exclude(orders__submitted_on__isnull=True)
                .count()
            )
            cart_count = None
            booking_count = None
            if instance.order_group.user.user_group:
                booking_count = (
                    OrderGroup.objects.filter(
                        user_address__user_group_id=instance.order_group.user.user_group_id
                    )
                    .exclude(orders__submitted_on__isnull=True)
                    .count()
                )
                cart_count = (
                    OrderGroup.objects.filter(
                        user_address__user_group_id=instance.order_group.user.user_group_id
                    )
                    .filter(orders__submitted_on__isnull=True)
                    .count()
                )

            line_items = []
            order_line_items = instance.order_line_items.all().select_related(
                "order_line_item_type"
            )
            for order_line_item in order_line_items:
                line_items.append(
                    {
                        "id": str(order_line_item.id),
                        "type_name": order_line_item.order_line_item_type.name,
                        "type_units": order_line_item.order_line_item_type.name,
                        "type_code": order_line_item.order_line_item_type.name,
                        "stripe_tax_code_id": order_line_item.order_line_item_type.name,
                        "rate": str(order_line_item.rate),
                        "quantity": str(order_line_item.quantity),
                        "platform_fee_percent": str(
                            order_line_item.platform_fee_percent
                        ),
                        "tax": str(order_line_item.tax)
                        if order_line_item.tax
                        else None,
                        "description": order_line_item.description,
                        "is_flat_rate": order_line_item.is_flat_rate,
                        "stripe_invoice_line_item_id": order_line_item.stripe_invoice_line_item_id,
                        "paid": order_line_item.paid,
                        "backbill": order_line_item.backbill,
                        "stripe_description": order_line_item.stripe_description,
                        "payment_status": order_line_item.payment_status(),
                        "seller_payout_price": str(
                            order_line_item.seller_payout_price()
                        ),
                        "customer_price_with_tax": str(
                            order_line_item.customer_price_with_tax()
                        ),
                    }
                )
            adjustments = []
            for adjustment in instance.order_items:
                adjustments.append(
                    {
                        "id": str(adjustment.id),
                        "name": adjustment.__class__.__name__,
                        "quantity": str(adjustment.quantity),
                        "customer_rate": str(adjustment.customer_rate),
                        "seller_rate": str(adjustment.seller_rate),
                        "stripe_invoice_line_item_id": adjustment.stripe_invoice_line_item_id,
                        "description": adjustment.description,
                    }
                )

            event_data = {
                "id": str(instance.id),
                "user": str(instance.order_group.user_id),
                "submitted_on": instance.submitted_on.isoformat()
                if instance.submitted_on
                else None,
                "status": instance.status,
                "customer_price_with_tax": str(instance.customer_price()),
                "seller_price": str(instance.seller_price()),
                "take_rate": str(instance.take_rate),
                "order_line_items": line_items,
                "adjustments": adjustments,
                "shipping_address": str(
                    instance.order_group.user_address.formatted_address()
                ),
                "customer_name": instance.order_group.user.full_name,
            }
            if (
                instance.order_group.user.user_group
                and hasattr(instance.order_group.user.user_group, "legal")
                and instance.order_group.user.user_group.legal
            ):
                event_data["customer_business_name"] = (
                    instance.order_group.user.user_group.legal.name
                )

            if (
                instance.order_group.user.user_group
                and hasattr(instance.order_group.user.user_group, "billing")
                and instance.order_group.user.user_group.billing
            ):
                event_data["billing_address"] = (
                    instance.order_group.user.user_group.billing.formatted_address
                )

            send_event(instance.order_group.user.email, event_name, event_data)
            update_person(
                instance.order_group.user.email,
                {"booking_count": user_booking_count, "cart_count": user_cart_count},
            )
            if instance.order_group.user.user_group:
                update_company(
                    instance.order_group.user.email,
                    str(instance.order_group.user.user_group_id),
                    {"booking_count": booking_count, "cart_count": cart_count},
                )
        except Exception as e:
            logger.exception(f"on_order_post_save2: [{instance.id}]-[{e}]")

    if settings.ENVIRONMENT == "TEST":
        p = threading.Thread(target=_send_event)
        p.start()
