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
from django.db.models import OuterRef, Subquery, ExpressionWrapper, DateField, Func, Value, CharField
from django.utils.timezone import now
from datetime import timedelta

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

        # New Buyers.
        new_buyers = UserGroup.objects.filter(
            account_owner=user,
            user_addresses__order_groups__orders__start_date__gte=first_of_month
        ).distinct().count()
        user.new_buyers = new_buyers

        # Orders created internally vs externally
        internal_orders_count = orders_for_user.filter(created_by__is_staff=True).count()
        external_orders_count = orders_for_user.filter(created_by__is_staff=False).count()

        user.internal_orders_count = internal_orders_count
        user.external_orders_count = external_orders_count

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
    max_end_date_subquery = Order.objects.filter(
        order_group=OuterRef('order_group')
    ).values('order_group').annotate(
        max_end_date=Max('end_date')
    ).values('max_end_date')

    today = now().date()

    orders = Order.objects.filter(
        order_group__user_address__user_group__account_owner_id=user_id
    ).annotate(
        order_id=F("id"),
        annotated_order_group_id=F("order_group__id"),
        order_end_date=F("end_date"),
        user_address_name=F("order_group__user_address__name"),
        account_owner_first_name=F("order_group__user_address__user_group__account_owner__first_name"),
        account_owner_last_name=F("order_group__user_address__user_group__account_owner__last_name"),
        user_first_name=F("order_group__user__first_name"),
        user_last_name=F("order_group__user__last_name"),
        user_email=F("order_group__user__email"),
        order_status=F("status"),
        sellerlocation_name=F("order_group__seller_product_seller_location__seller_location__name"),
        mainproduct_name=F("order_group__seller_product_seller_location__seller_product__product__main_product__name"),
        is_most_recent_order=Case(
            When(order_end_date=Subquery(max_end_date_subquery), then=True),
            default=False,
            output_field=BooleanField()
        ),
        autorenewal_date=ExpressionWrapper(
            F("order_end_date") + timedelta(days=28),
            output_field=DateField(),
        ),
        take_action=Case(
            When(autorenewal_date__lte=today + timedelta(days=10), then=True),
            default=False,
            output_field=BooleanField()
        ),
        order_group_url_annotate=Func(
            Value(settings.DASHBOARD_BASE_URL + "/"),
            Value("admin/api/ordergroup/"),
            F("order_group__id"),
            Value("/change/"),
            function="CONCAT",
            output_field=CharField(),
        ),
    ).values(
        "order_id", "annotated_order_group_id", "order_end_date", "user_address_name", "account_owner_first_name",
        "account_owner_last_name", "user_first_name", "user_last_name", "user_email", "order_status",
        "sellerlocation_name", "mainproduct_name", "is_most_recent_order", "autorenewal_date", "take_action", 
        "order_group_url_annotate"
    )

    context["orders"] = orders

    context["user"] = user
    return render(request, "dashboards/user_sales_28_day_list.html", context)


def user_sales_new_buyers(request, user_id):
    context = {}
    try:
        user = User.objects.get(id=user_id, is_staff=True, groups__name="Sales")
    except User.DoesNotExist:
        return render(request, "404.html", status=404)
    
    
    user_groups = UserGroup.objects.filter(
        account_owner=user,
        user_addresses__order_groups__orders__end_date__gte=timezone.now() - timedelta(days=30)
    ).distinct().values('id', 'name', 'user_addresses__order_groups__start_date')


    context["user_groups"] = user_groups
    context["user"] = user

    return render(request, "dashboards/user_sales_new_buyers.html", context)
