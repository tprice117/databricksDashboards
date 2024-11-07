from django.db.models import Q
from django.utils import timezone

from api.models import Order, OrderGroup


def create_auto_renewal_orders(request):
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

    for order_group in active_order_groups:
        # Only process if the OrderGroup has Orders.
        if order_group.orders.exists():
            # Get the most recent Order for the OrderGroup.
            most_recent_order: Order = order_group.orders.order_by("-end_date").first()

            # Get the most recent Order EndDate at 11:59:59 PM.
            most_recent_order_end_date = most_recent_order.end_date.replace(
                hour=23,
                minute=59,
                second=59,
            )

            # Get 28 days ago at 12:00:00 AM.
            twenty_eight_days_ago = timezone.now() - timezone.timedelta(days=28)
            twenty_eight_days_ago = twenty_eight_days_ago.replace(
                hour=0,
                minute=0,
                second=0,
            )

            # If the most recent Order.EndDate is more than 28 days in the past,
            # create a new Order for the OrderGroup.
            if most_recent_order_end_date < twenty_eight_days_ago:
                Order.objects.create(
                    order_group=order_group,
                    start_date=most_recent_order_end_date + timezone.timedelta(days=1),
                    end_date=most_recent_order_end_date + timezone.timedelta(days=29),
                    status=Order.Status.PENDING,
                )
