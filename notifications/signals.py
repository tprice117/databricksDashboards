from django.db.models.signals import post_save
from django.template.loader import render_to_string
# import threading
import logging
from api.models import Order
from communications.intercom.utils.utils import get_json_safe_value
from notifications.utils.add_email_to_queue import add_email_to_queue

logger = logging.getLogger(__name__)

"""Order track fields needed for sending email notifications on Order submitted and Order status changed.
If another field needs to be tracked, go to the model class and edit the
track_data class decorator parameters.

Django Signals help: https://docs.djangoproject.com/en/5.0/topics/signals/
"""


def get_order_status_from_choice(status: str) -> str:
    """Get the status from Order.STATUS_CHOICES.

    Args:
        status (str): The db status value.

    Returns:
        str: The human readable status.
    """
    for choice in Order.STATUS_CHOICES:
        if choice[0] == status:
            return choice[1]
    return "Unknown"


# ================================================#
# Email on Order database actions
# ================================================#

def on_order_post_save(sender, **kwargs):
    """Sends an email on Order database actions, such as Order submitted or Order status changed.
    """
    order: Order = kwargs.get('instance', None)
    if kwargs.get('created', False) is False:
        # Order updated
        error_status = "created-Order"
        order_id = get_json_safe_value(order.id)
        try:
            if order.submitted_on is not None:
                if order.old_value('submitted_on') is None:
                    # Order submitted
                    subject = "Thanks for your order!"
                    html_content = render_to_string(
                        "notifications/emails/order_submitted.html",
                        {"order": order}
                    )
                    add_email_to_queue(
                        from_email="dispatch@trydownstream.com",
                        to_emails=[order.order_group.user.email],
                        subject=subject,
                        html_content=html_content,
                        reply_to="dispatch@trydownstream.com"
                    )
                elif order.old_value('status') != order.status:
                    error_status = "updated-Order"
                    # Order status changed
                    subject = "An update on your Downstream order"
                    html_content = render_to_string(
                        "notifications/emails/order_status_change.html",
                        {
                            "order": order,
                            "new_status": get_order_status_from_choice(order.status),
                            "previous_status": get_order_status_from_choice(order.old_value('status'))
                        }
                    )
                    add_email_to_queue(
                        from_email="dispatch@trydownstream.com",
                        to_emails=[order.order_group.user.email],
                        subject=subject,
                        html_content=html_content,
                        reply_to="dispatch@trydownstream.com"
                    )
        except Exception as e:
            logger.exception(f"notification: [{order_id}]-[{error_status}]-[{e}]")


post_save.connect(on_order_post_save, sender=Order)
