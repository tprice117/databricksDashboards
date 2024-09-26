import logging

from django.contrib.auth.decorators import login_required

from api.models import User

logger = logging.getLogger(__name__)

from django.shortcuts import render
from django.utils import timezone

from api.models.order.order import *
from api.models.order.order_group import *
from api.models.order.order_line_item import *
from api.models.seller.seller import *
from api.models.user.user_group import *


@login_required(login_url="/admin/login/")
def sales_leaderboard(request):
    # Get the first of the month.
    current_month = timezone.now().month
    first_of_month = timezone.now().replace(
        day=1,
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )

    # Get Orders for the current month.
    orders_this_month = Order.objects.all()

    # Get all Users.
    users = User.objects.all()

    # For each User, add their aggregated Order data for this month.
    for user in users:
        orders_for_user = orders_this_month.filter(
            order_group__user_address__user_group__account_owner=user,
        )

        # Total GMV.
        user.gmv = sum([order.customer_price() for order in orders_for_user])

        # Average Discount.
        user.avg_discount = (
            sum(
                [
                    (
                        (order.customer_price() - order.seller_price())
                        / order.customer_price()
                        * 100
                        if order.customer_price() > 0
                        else 0
                    )
                    for order in orders_for_user
                ]
            )
            / len(orders_for_user)
            if len(orders_for_user) > 0
            else 0
        )

        # Net Revenue.
        user.net_revenue = sum(
            [order.customer_price() - order.seller_price() for order in orders_for_user]
        )

        # Order Count.
        user.order_count = len(orders_for_user)

    # Sort Users by GMV (descending).
    users = sorted(users, key=lambda user: user.gmv, reverse=True)

    return render(
        request,
        "dashboards/sales_leaderboard.html",
        {
            "users": users,
        },
    )
