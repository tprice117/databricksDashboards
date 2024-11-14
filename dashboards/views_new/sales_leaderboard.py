import logging

from django.contrib.auth.decorators import login_required

from api.models import User

logger = logging.getLogger(__name__)
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Count, Case, When, BooleanField

from api.models.order.order import *
from api.models.order.order_group import *
from api.models.order.order_line_item import *
from api.models.seller.seller import *
from api.models.user.user_group import *
from django.db.models import Sum, F, Max
from django.db.models.functions import Substr, StrIndex

# Define first_of_month and orders_this_month outside the views
first_of_month = timezone.now().replace(
    day=1,
    hour=0,
    minute=0,
    second=0,
    microsecond=0,
)

orders_this_month = Order.objects.filter(
    end_date__gte=first_of_month,
    status=Order.Status.COMPLETE,
)


@login_required(login_url="/admin/login/")
def sales_leaderboard(request):
    # Get all Users.
    users = User.objects.filter(
        is_staff=True,
        groups__name="Sales",
    )

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


def user_sales_detail(request, user_id):
    context = {}
    try:
        user = User.objects.get(id=user_id, is_staff=True, groups__name="Sales")
    except User.DoesNotExist:
        return render(request, "404.html", status=404)

    orders_for_user = orders_this_month.filter(
        order_group__user_address__user_group__account_owner=user,
    )
    order_count = len(orders_for_user)
    context["user"] = user
    context["orders"] = orders_this_month
    context["ordersforuser"] = orders_for_user
    context["order_count"] = order_count
    return render(request, "dashboards/user_sales_detail.html", context)


def user_sales_product_mix(request, user_id):
    context = {}
    try:
        user = User.objects.get(id=user_id, is_staff=True, groups__name="Sales")
    except User.DoesNotExist:
        return render(request, "404.html", status=404)

    orders_for_user = orders_this_month.filter(
        order_group__user_address__user_group__account_owner=user,
    )
    # Group orders by product name.
    product_sales = (
        orders_for_user.values(
            main_product_name=F(
                "order_group__seller_product_seller_location__seller_product__product__main_product__name"
            )
        )
        .annotate(order_count=Count("id"))
        .order_by("order_count")
    )

    # Prepare data for the pie chart.
    product_names = [product["main_product_name"] for product in product_sales]
    order_counts = [product["order_count"] for product in product_sales]

    # Include Chart.js script and data in the context.
    context["chart_data"] = {
        "labels": product_names,
        "datasets": [
            {
                "data": order_counts,
                "backgroundColor": [
                    "#FF6384",
                    "#36A2EB",
                    "#FFCE56",
                    "#4BC0C0",
                    "#9966FF",
                    "#FF9F40",
                ],
            }
        ],
    }
    context["product_sales"] = product_sales
    context["user"] = user
    context["orders_this_month"] = orders_this_month
    return render(request, "dashboards/user_sales_product_mix.html", context)


def user_sales_top_accounts(request, user_id):
    context = {}
    try:
        user = User.objects.get(id=user_id, is_staff=True, groups__name="Sales")
    except User.DoesNotExist:
        return render(request, "404.html", status=404)
    orders_for_user = orders_this_month.filter(
        order_group__user_address__user_group__account_owner=user,
    )
    # Group orders by seller location name.
    top_accounts = (
        orders_for_user.values(
            seller_location_name=F(
                "order_group__seller_product_seller_location__seller_location__name"
            )
        )
        .annotate(order_count=Count("id"))
        .order_by("-order_count")
    )

    context["top_accounts"] = top_accounts
    context["user"] = user
    return render(request, "dashboards/user_sales_top_accounts.html", context)


def user_sales_new_accounts(request, user_id):
    context = {}
    try:
        user = User.objects.get(id=user_id, is_staff=True, groups__name="Sales")
    except User.DoesNotExist:
        return render(request, "404.html", status=404)
    orders_for_user = orders_this_month.filter(
        order_group__user_address__user_group__account_owner=user,
    )
    # Filter user groups with their order group start date and order most recent order date.
    new_accounts = (
        orders_for_user.filter(
            order_group__start_date__gte=first_of_month - timezone.timedelta(days=30)
        )
        .values(
            seller_location_name=F(
                "order_group__seller_product_seller_location__seller_location__name"
            ),
            order_group_start_date=F("order_group__start_date"),
            order_most_recent_order_date=F("end_date"),
        )
        .distinct()
    )

    context["new_accounts"] = new_accounts
    context["user"] = user
    return render(request, "dashboards/user_sales_new_accounts.html", context)


def user_sales_churned_accounts(request, user_id):
    context = {}
    try:
        user = User.objects.get(id=user_id, is_staff=True, groups__name="Sales")
    except User.DoesNotExist:
        return render(request, "404.html", status=404)

    orders_for_user = Order.objects.filter(
        order_group__user_address__user_group__account_owner=user,
    )
    user_groups_for_user = UserGroup.objects.filter(account_owner=user)

    # Find user groups that have not placed any orders in the last 30 days.
    churned_accounts = user_groups_for_user

    context["churned_accounts"] = churned_accounts
    context["user"] = user
    return render(request, "dashboards/user_sales_churned_accounts.html", context)


def user_sales_28_day_list(request, user_id):
    context = {}
    try:
        user = User.objects.get(id=user_id, is_staff=True, groups__name="Sales")
    except User.DoesNotExist:
        return render(request, "404.html", status=404)
    orders_for_user = Order.objects.filter(
        order_group__user_address__user_group__account_owner=user,
        end_date__gte=timezone.now() - timezone.timedelta(days=28),
        status=Order.Status.COMPLETE,
    ).annotate(
        annotated_order_group_id=F("order_group__id"),
        order_group_end_date=F("order_group__end_date"),
        order_end_date=F("end_date"),
        order_id=F("id"),
        user_account_owner=F(
            "order_group__user_address__user_group__account_owner__username"
        ),
        user_address_name=F("order_group__user_address__name"),
        user_first_name=F(
            "order_group__user_address__user_group__account_owner__first_name"
        ),
        user_last_name=F(
            "order_group__user_address__user_group__account_owner__last_name"
        ),
        user_email=F("order_group__user_address__user_group__account_owner__email"),
        order_status=F("status"),
        seller_location_name=F(
            "order_group__seller_product_seller_location__seller_location__name"
        ),
        main_product_name=F(
            "order_group__seller_product_seller_location__seller_product__product__main_product__name"
        ),
        take_action=Case(
            When(end_date__lte=timezone.now() + timezone.timedelta(days=10), then=True),
            default=False,
            output_field=BooleanField(),
        ),
    )

    context["orders_for_user"] = orders_for_user

    context["user"] = user
    return render(request, "dashboards/user_sales_28_day_list.html", context)


def user_sales_new_buyers(request, user_id):
    context = {}
    try:
        user = User.objects.get(id=user_id, is_staff=True, groups__name="Sales")
    except User.DoesNotExist:
        return render(request, "404.html", status=404)

    context["user"] = user
    return render(request, "dashboards/user_sales_new_buyers.html", context)
