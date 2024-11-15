import datetime

from django.db.models import Q
from django.utils import timezone

from api.models import Order, OrderGroup
from notifications.utils.add_email_to_queue import add_internal_email_to_queue


def create_auto_renewal_orders():
    """
    For any OrderGroup, if the most recent Order.EndDate is more than 28
    days in the past, create a new Order for the OrderGroup with a StartDate
    of the most recent Order.EndDate and an EndDate of the most recent
    Order.EndDate + 28 days.
    """

    # Get all OrderGroups with a NULL EndDate or an EndDate in the future.
    # These are the OrderGroups that are currently active.
    active_order_groups = OrderGroup.objects.filter(
        Q(end_date__gte=timezone.now()) | Q(end_date__isnull=True)
    )

    # Create list of OrderGroups that need to auto-renew.
    order_groups_that_needs_to_auto_renew = []

    for order_group in active_order_groups:
        # Only process if the OrderGroup has submitted Orders.
        submitted_orders = order_group.orders.filter(
            submitted_on__isnull=False,
        ).order_by("-start_date")

        if submitted_orders.exists():
            # Get the most recent Order for the OrderGroup.
            most_recent_submitted_order: Order = submitted_orders.first()

            # Get the most recent Order StartDate at 11:59:59 PM.
            most_recent_submitted_order_start_date = datetime.datetime(
                most_recent_submitted_order.start_date.year,
                most_recent_submitted_order.start_date.month,
                most_recent_submitted_order.start_date.day,
                23,
                59,
                59,
            )

            # Get the most recent Order EndDate at 11:59:59 PM.
            most_recent_submitted_order_end_date = (
                datetime.datetime(
                    most_recent_submitted_order.end_date.year,
                    most_recent_submitted_order.end_date.month,
                    most_recent_submitted_order.end_date.day,
                    23,
                    59,
                    59,
                )
                if most_recent_submitted_order.end_date
                else None
            )

            # Use the most recent Order EndDate as the reference point,
            # if it exists. Otherwise, use the most recent Order StartDate.
            reference_date = (
                most_recent_submitted_order_end_date
                or most_recent_submitted_order_start_date
            )

            # Get 28 days ago at 12:00:00 AM.
            twenty_eight_days_ago = timezone.now() - timezone.timedelta(days=28)
            twenty_eight_days_ago = datetime.datetime(
                twenty_eight_days_ago.year,
                twenty_eight_days_ago.month,
                twenty_eight_days_ago.day,
                0,
                0,
                0,
            )

            # If the most recent Order.StartDate is more than 28 days in the past,
            # create a new Order for the OrderGroup.

            if reference_date < twenty_eight_days_ago:
                # Add the OrderGroup to the list of OrderGroups that need to
                # auto-renew.
                order_groups_that_needs_to_auto_renew.append(
                    order_group,
                )

                # # Set the most recent Order EndDate, if not already set.
                # if most_recent_submitted_order_end_date is None:
                #     most_recent_submitted_order_end_date = (
                #         most_recent_submitted_order_start_date
                #         + timezone.timedelta(days=29)
                #     )

                # # If there are unsubmitted Orders after the most recent
                # # submitted Order, delete them.
                # order_group.orders.filter(
                #     submitted_on__isnull=True,
                # ).delete()

                # Order.objects.create(
                #     order_group=order_group,
                #     start_date=most_recent_submitted_order_end_date
                #     + timezone.timedelta(days=1),
                #     end_date=most_recent_submitted_order_end_date
                #     + timezone.timedelta(days=29),
                #     status=Order.Status.PENDING,
                # )

    # Send email to admins showing the OrderGroup that needs to auto-renew.
    # In the html_content, show a list of the OrderGroups that need to auto-renew.
    # The list should be a bulleted list of OrderGroup admin URLs.
    add_internal_email_to_queue(
        subject="BETA (Not Creating Orders): OrderGroups That Need Auto-Renewal",
        html_content="OrderGroups that need to auto-renew: <ul>{}</ul>".format(
            "".join(
                [
                    f"<li><a href='https://portal.trydownstream.com/admin/api/ordergroup/{order_group.id}/change/'>{order_group.id}</a></li>"
                    for order_group in order_groups_that_needs_to_auto_renew
                ]
            )
        ),
    )
