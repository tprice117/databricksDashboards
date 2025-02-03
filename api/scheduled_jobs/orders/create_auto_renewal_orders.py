import datetime

from django.conf import settings
from django.db.models import F, Q
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

    # Double check that only active OrderGroups are being processed.
    active_order_groups = [
        order_group for order_group in active_order_groups if order_group.is_active
    ]

    # Do not auto-renew Temporary Fencing OrderGroups.
    active_order_groups = [
        order_group
        for order_group in active_order_groups
        if not order_group.seller_product_seller_location.seller_product.product.main_product.main_product_category.main_product_category_code
        == "FENCE"
    ]

    # Do not auto-renew Dumpster OrderGroups.
    active_order_groups = [
        order_group
        for order_group in active_order_groups
        if not order_group.seller_product_seller_location.seller_product.product.main_product.main_product_category.main_product_category_code
        == "RO"
    ]

    # Create list of OrderGroups that need to auto-renew.
    order_groups_that_needs_to_auto_renew = []

    for order_group in active_order_groups:
        # Only process if the OrderGroup has submitted Orders.
        submitted_orders = order_group.orders.filter(
            submitted_on__isnull=False,
        ).order_by(
            F("end_date").desc(nulls_first=True),
        )

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

            # If the OrderGroup's MainProduct.has_rental_multi_step = TRUE (is a multi-step rental),
            # then check if the "accumulated" rental cost for the current period has reached the
            # monthly price. If it has, create a new Order for the OrderGroup.
            has_surpassed_monthly = (
                _multi_step_rental_has_surpassed_monthly(order_group)
                if order_group.seller_product_seller_location.seller_product.product.main_product.has_rental_multi_step
                else False
            )

            # If the most recent Order.StartDate is more than 28 days in the past,
            # create a new Order for the OrderGroup.
            if reference_date < twenty_eight_days_ago or has_surpassed_monthly:
                # Add the OrderGroup to the list of OrderGroups that need to
                # auto-renew.
                order_groups_that_needs_to_auto_renew.append(
                    order_group,
                )

                # If there are unsubmitted Orders after the most recent
                # submitted Order, delete them.
                order_group.orders.filter(
                    submitted_on__isnull=True,
                ).delete()

                Order.objects.create(
                    order_group=order_group,
                    start_date=most_recent_submitted_order_end_date,
                    end_date=most_recent_submitted_order_end_date
                    + timezone.timedelta(days=28),
                    status=Order.Status.COMPLETE,
                    submitted_on=timezone.now(),
                )

    # Only send emails in the PROD environment.
    if settings.ENVIRONMENT == "TEST":
        # Send email to admins showing the OrderGroup that needs to auto-renew.
        # In the html_content, show a list of the OrderGroups that need to auto-renew.
        # The list should be a bulleted list of OrderGroup admin URLs.
        add_internal_email_to_queue(
            subject="Auto Renewals: OrderGroups that have been auto-renewed",
            html_content="OrderGroups that have been auto-renewed: <ul>{}</ul>".format(
                "".join(
                    [
                        f"<li><a href='{settings.DASHBOARD_BASE_URL}/admin/api/ordergroup/{order_group.id}/change/'>{order_group.id}</a></li>"
                        for order_group in order_groups_that_needs_to_auto_renew
                    ]
                )
            ),
        )


def _multi_step_rental_has_surpassed_monthly(order_group: OrderGroup) -> bool:
    """
    Check if the accumulated rental cost for the current period has reached the
    monthly price. If no monthly price is set, return FALSE.
    """
    if hasattr(order_group, "rental_multi_step"):
        # Get most recent Order for the OrderGroup.
        most_recent_order: Order = (
            (
                order_group.orders.filter(
                    submitted_on__isnull=False,
                )
                .order_by("-end_date")
                .first()
            )
            if order_group.orders.exists()
            else None
        )

        # Only process if the most recent Order is in the past.
        if most_recent_order and most_recent_order.end_date < timezone.now().date():
            # Get the accumulated rental cost for the current period.
            line_items = order_group.rental_multi_step.get_price(
                duration=timezone.now().date() - most_recent_order.end_date,
                shift_count=order_group.shift_count,
            )

            accumulated_rental_cost = sum(
                [line_item.total for line_item in line_items],
                0,
            )

            # Check if the accumulated rental cost for the current period has
            # reached the monthly price. If no monthly price is set, return FALSE.
            return (
                accumulated_rental_cost >= order_group.rental_multi_step.month
                if order_group.rental_multi_step.month
                else False
            )
        else:
            return False
    else:
        return False
