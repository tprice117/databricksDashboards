from django.db.models.signals import post_save
from django.template.loader import render_to_string
# import threading
import logging
from api.models import Order
from communications.intercom.utils.utils import get_json_safe_value
from notifications.utils.add_email_to_queue import add_email_to_queue

logger = logging.getLogger(__name__)

"""Order track fields needed for sending email notifications.
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


def get_tracked_data(db_obj: Order) -> dict:
    """Get tracked data as key:val dictionary. Only retrieve non None data.

    Args:
        db_obj (Order): The database object.

    Returns:
        dict: Non None data in key:val dict.
    """
    data = {}
    for key, val in db_obj.__data.items():
        dbval = get_json_safe_value(getattr(db_obj, key))
        if dbval is not None:
            data[key] = dbval
    return data


# ================================================#
# Email on Order database actions
# ================================================#

def on_order_post_save(sender, **kwargs):
    """Sends an email on Order database actions, such as Order submitted or Order status changed.
    """
    order: Order = kwargs.get('instance', None)
    if 'created' not in kwargs:
        # Order updated
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
                        html_content=html_content
                    )
                elif order.old_value('status') != order.status:
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
                        html_content=html_content
                    )
        except Exception as e:
            logger.exception(f"notification: [submitted-Order]-[{e}]")


post_save.connect(on_order_post_save, sender=Order)
