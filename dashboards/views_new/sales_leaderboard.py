import logging
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import (
    BooleanField,
    Case,
    CharField,
    Count,
    DateField,
    DurationField,
    ExpressionWrapper,
    F,
    Func,
    Max,
    OuterRef,
    Subquery,
    Sum,
    Value,
    When,
)
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.utils import timezone
from django.utils.timezone import now

from api.models import User
from api.models.order.order import Order
from api.models.user.user_group import UserGroup
from api_proxy import settings
from dashboards.views import get_sales_dashboard_context

logger = logging.getLogger(__name__)


def get_first_of_month():
    return timezone.now().replace(
        day=1,
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )


def get_sales_competition_start_date():
    return timezone.datetime(2024, 10, 1, 0, 0, 0, tzinfo=timezone.utc)


def get_orders_this_month(first_of_month):
    return Order.objects.filter(
        end_date__gte=first_of_month,
        status=Order.Status.COMPLETE,
    )


def get_max_new_buyers(first_of_month):
    return (
        UserGroup.objects.filter(
            user_addresses__order_groups__orders__start_date__gte=first_of_month
        )
        .distinct()
        .count()
    )


def get_max_gmv(orders_this_month):
    return (
        orders_this_month.aggregate(
            max_gmv=Sum(
                F("order_line_items__rate")
                * F("order_line_items__quantity")
                * (1 + F("order_line_items__platform_fee_percent") / 100)
            )
        )["max_gmv"]
        or 1
    )


def get_max_external_orders(orders_this_month):
    return orders_this_month.filter(created_by__is_staff=False).count()


def get_max_discount_rate():
    return 100  # Maximum possible discount rate


def calculate_standing_scores(users, attribute, inverse=False, non_zero_first=False):
    if non_zero_first:
        sorted_users = sorted(users, key=lambda user: (getattr(user, attribute) == 0, getattr(user, attribute)))
    else:
        sorted_users = sorted(users, key=lambda user: getattr(user, attribute), reverse=not inverse)
    
    total_users = len(users)
    current_score = total_users
    previous_value = None
    for index, user in enumerate(sorted_users):
        current_value = getattr(user, attribute)
        if current_value != previous_value:
            current_score = total_users - index
        setattr(user, f"{attribute}_score", current_score)
        previous_value = current_value


def calculate_total_score(user):
    total_score = (
        user.new_buyers_score * 0.4 +
        user.gmv_score * 0.25 +
        user.platform_adoption_score * 0.25 +
        user.discount_rate_score * 0.1
    )
    return total_score


def calculate_discount_rate(order):
    
    # Find the related Order Group
    order_group = order.order_group

    # Order Group relationship to SPSL
    spsl = order_group.seller_product_seller_location

    # SPSL relationship to Seller Product
    seller_product = spsl.seller_product

    # Seller Product to Product
    product = seller_product.product

    # Finally get Min and Default Take Rate on Main Product
    main_product = product.main_product
    min_take_rate = main_product.minimum_take_rate
    default_take_rate = main_product.default_take_rate

    # Take Min and Default back to #1 (Seller Price) to find Default Customer Price
    seller_price = order.seller_price()
    default_customer_price = seller_price * (1 + (default_take_rate / 100))

    # Calculate the minimum customer price using the min_take_rate
    min_customer_price = seller_price * (1 + (min_take_rate / 100))

    # Apply the Discount formula --> Default Price divided by actual Customer Price
    actual_customer_price = order.customer_price()
    
    if default_customer_price == 0:
        return 0

    discount_rate = ((default_customer_price - actual_customer_price) / default_customer_price) * 100

    # Ensure the discount rate does not exceed the maximum allowed discount
    max_discount = ((default_customer_price - min_customer_price) / default_customer_price) * 100
    if discount_rate > max_discount:
        discount_rate = max_discount

    return discount_rate

# @login_required(login_url="/admin/login/")
def sales_leaderboard(request):
    # Get all Users.
    users = User.objects.filter(
        is_staff=True,
        groups__name="Sales",
    )

    # Get orders for this month
    first_of_month = get_first_of_month()
    orders_this_month = get_orders_this_month(first_of_month)

    # For each User, add their aggregated Order data for this month.
    for user in users:
        orders_for_user = orders_this_month.filter(
            order_group__user_address__user_group__account_owner=user,
        )

        # Total GMV.
        user.gmv = sum([order.customer_price() for order in orders_for_user])

        # Average Discount.
        user.avg_discount = (
            sum([calculate_discount_rate(order) for order in orders_for_user])
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
        new_buyers = (
            UserGroup.objects.filter(
                account_owner=user,
                user_addresses__order_groups__orders__start_date__gte=first_of_month,
            )
            .distinct()
            .count()
        )
        user.new_buyers = new_buyers

        # Orders created internally vs externally
        internal_orders_count = orders_for_user.filter(
            created_by__is_staff=True
        ).count()
        external_orders_count = orders_for_user.filter(
            created_by__is_staff=False
        ).count()

        user.internal_orders_count = internal_orders_count
        user.external_orders_count = external_orders_count

    # Calculate scores based on standings
    calculate_standing_scores(users, "new_buyers")
    calculate_standing_scores(users, "gmv")
    calculate_standing_scores(users, "external_orders_count")
    calculate_standing_scores(users, "avg_discount", inverse=True, non_zero_first=True)

    # Calculate total score and weighted scores for each user
    for user in users:
        user.platform_adoption_score = user.external_orders_count_score
        user.discount_rate_score = user.avg_discount_score
        user.new_buyers_weighted_score = user.new_buyers_score * 0.4
        user.gmv_weighted_score = user.gmv_score * 0.25
        user.platform_adoption_weighted_score = user.platform_adoption_score * 0.25
        user.discount_rate_weighted_score = user.discount_rate_score * 0.1
        user.score = calculate_total_score(user)

    # Sort Users by total score (descending).
    users = sorted(users, key=lambda user: user.score, reverse=True)
    return render(
        request,
        "dashboards/sales_leaderboard.html",
        {
            "users": users,
        },
    )


def user_sales_detail(request, user_id):
    if request.user.id != user_id and request.user.type != "ADMIN":
        return HttpResponseForbidden("You are not allowed to access this page.")

    context = {}
    try:
        user = User.objects.get(id=user_id, is_staff=True, groups__name="Sales")
    except User.DoesNotExist:
        return render(request, "404.html", status=404)

    first_of_month = get_first_of_month()
    orders_this_month = get_orders_this_month(first_of_month)
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
    if request.user.id != user_id and request.user.type != "ADMIN":
        return HttpResponseForbidden("You are not allowed to access this page.")

    context = {}
    try:
        user = User.objects.get(id=user_id, is_staff=True, groups__name="Sales")
    except User.DoesNotExist:
        return render(request, "404.html", status=404)

    first_of_month = get_first_of_month()
    orders_this_month = get_orders_this_month(first_of_month)
    orders_for_user = orders_this_month.filter(
        order_group__user_address__user_group__account_owner=user,
    )
    # Group orders by product name.
    product_sales = (
        orders_for_user.values(
            main_product_category=F(
                "order_group__seller_product_seller_location__seller_product__product__main_product__main_product_category__name"
            )
        )
        .annotate(order_count=Count("id"))
        .order_by("order_count")
    )

    # Prepare data for the pie chart.
    product_names = [product["main_product_category"] for product in product_sales]
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
    if request.user.id != user_id and request.user.type != "ADMIN":
        return HttpResponseForbidden("You are not allowed to access this page.")
    context = {}
    try:
        user = User.objects.get(id=user_id, is_staff=True, groups__name="Sales")
    except User.DoesNotExist:
        return render(request, "404.html", status=404)

    first_of_month = get_first_of_month()
    orders_this_month = get_orders_this_month(first_of_month)
    orders_for_user = orders_this_month.filter(
        order_group__user_address__user_group__account_owner=user,
    )
    # Group orders by seller location name.
    top_accounts = (
        orders_for_user.values(
            user_group_name=F("order_group__user_address__user_group__name")
        )
        .annotate(order_count=Count("id"))
        .order_by("-order_count")
    )

    context["top_accounts"] = top_accounts
    context["user"] = user
    return render(request, "dashboards/user_sales_top_accounts.html", context)


def user_sales_new_accounts(request, user_id):
    if request.user.id != user_id and request.user.type != "ADMIN":
        return HttpResponseForbidden("You are not allowed to access this page.")
    context = {}
    try:
        user = User.objects.get(id=user_id, is_staff=True, groups__name="Sales")
    except User.DoesNotExist:
        return render(request, "404.html", status=404)

    first_of_month = get_first_of_month()
    orders_this_month = get_orders_this_month(first_of_month)
    orders_for_user = orders_this_month.filter(
        order_group__user_address__user_group__account_owner=user,
    )
    # Filter user groups with their order group start date and order most recent order date.
    new_accounts = (
        orders_for_user.filter(
            order_group__start_date__gte=first_of_month - timezone.timedelta(days=30)
        )
        .values(
            user_group_name=F("order_group__user_address__user_group__name"),
            order_group_start_date=F("order_group__start_date"),
            order_most_recent_order_date=F("end_date"),
        )
        .distinct()
    )

    context["new_accounts"] = new_accounts
    context["user"] = user
    return render(request, "dashboards/user_sales_new_accounts.html", context)


def user_sales_churned_accounts(request, user_id):
    if request.user.id != user_id and request.user.type != "ADMIN":
        return HttpResponseForbidden("You are not allowed to access this page.")
    context = {}
    try:
        user = User.objects.get(id=user_id, is_staff=True, groups__name="Sales")
    except User.DoesNotExist:
        return render(request, "404.html", status=404)

    user_groups_for_user = UserGroup.objects.filter(account_owner=user)

    # Find user groups that have not placed any orders in the last 30 days.
    churned_accounts = (
        user_groups_for_user.annotate(
            last_order_date=Max("user_addresses__order_groups__orders__end_date")
        )
        .filter(last_order_date__lt=timezone.now().date() - timedelta(days=30))
        .annotate(
            days_since_last_order=ExpressionWrapper(
                timezone.now().date() - F("last_order_date"),
                output_field=DurationField(),
            )
        )
        .values("id", "name", "last_order_date", "days_since_last_order")
    )

    # Remove hours, minutes, and seconds from days_since_last_order
    for account in churned_accounts:
        account["days_since_last_order"] = account["days_since_last_order"].days

    context["churned_accounts"] = churned_accounts
    context["user"] = user
    return render(request, "dashboards/user_sales_churned_accounts.html", context)


def user_sales_28_day_list(request, user_id):
    if request.user.id != user_id and request.user.type != "ADMIN":
        return HttpResponseForbidden("You are not allowed to access this page.")
    context = {}
    try:
        user = User.objects.get(id=user_id, is_staff=True, groups__name="Sales")
    except User.DoesNotExist:
        return render(request, "404.html", status=404)
    max_end_date_subquery = (
        Order.objects.filter(order_group=OuterRef("order_group"))
        .values("order_group")
        .annotate(max_end_date=Max("end_date"))
        .values("max_end_date")
    )

    today = now().date()

    orders = (
        Order.objects.filter(
            order_group__user_address__user_group__account_owner_id=user_id,
            order_group__end_date__isnull=True,
        )
        .annotate(
            order_id=F("id"),
            annotated_order_group_id=F("order_group__id"),
            order_end_date=F("end_date"),
            user_address_name=F("order_group__user_address__name"),
            account_owner_first_name=F(
                "order_group__user_address__user_group__account_owner__first_name"
            ),
            account_owner_last_name=F(
                "order_group__user_address__user_group__account_owner__last_name"
            ),
            user_first_name=F("order_group__user__first_name"),
            user_last_name=F("order_group__user__last_name"),
            user_email=F("order_group__user__email"),
            order_status=F("status"),
            sellerlocation_name=F(
                "order_group__seller_product_seller_location__seller_location__name"
            ),
            mainproduct_name=F(
                "order_group__seller_product_seller_location__seller_product__product__main_product__name"
            ),
            is_most_recent_order=Case(
                When(order_end_date=Subquery(max_end_date_subquery), then=True),
                default=False,
                output_field=BooleanField(),
            ),
            autorenewal_date=ExpressionWrapper(
                F("order_end_date") + timedelta(days=28),
                output_field=DateField(),
            ),
            take_action=Case(
                When(autorenewal_date__lte=today + timedelta(days=10), then=True),
                default=False,
                output_field=BooleanField(),
            ),
            order_group_url_annotate=Func(
                Value(settings.DASHBOARD_BASE_URL + "/"),
                Value("admin/api/ordergroup/"),
                F("order_group__id"),
                Value("/change/"),
                function="CONCAT",
                output_field=CharField(),
            ),
        )
        .filter(is_most_recent_order=True, take_action=True)
        .values(
            "order_id",
            "annotated_order_group_id",
            "order_end_date",
            "user_address_name",
            "account_owner_first_name",
            "account_owner_last_name",
            "user_first_name",
            "user_last_name",
            "user_email",
            "order_status",
            "sellerlocation_name",
            "mainproduct_name",
            "is_most_recent_order",
            "autorenewal_date",
            "take_action",
            "order_group_url_annotate",
        )
    )
    total_order_count = orders.count()
    context["total_order_count"] = total_order_count

    context["orders"] = orders

    context["user"] = user
    return render(request, "dashboards/user_sales_28_day_list.html", context)


def user_sales_new_buyers(request, user_id):
    if request.user.id != user_id and request.user.type != "ADMIN":
        return HttpResponseForbidden("You are not allowed to access this page.")
    context = {}
    try:
        user = User.objects.get(id=user_id, is_staff=True, groups__name="Sales")
    except User.DoesNotExist:
        return render(request, "404.html", status=404)

    first_of_month = get_first_of_month()
    orders_this_month = get_orders_this_month(first_of_month)
    user_groups = (
        UserGroup.objects.filter(
            account_owner=user,
            user_addresses__order_groups__orders__end_date__gte=first_of_month,
        )
        .distinct()
        .values("id", "name", "user_addresses__order_groups__start_date")
    )

    user_groups = user_groups.annotate(
        transaction_date=Max("user_addresses__order_groups__orders__end_date"),
        order_user_name=F("user_addresses__order_groups__orders__created_by__username"),
    )
    context["user_groups"] = user_groups
    context["user"] = user

    return render(request, "dashboards/user_sales_new_buyers.html", context)


def user_sales_metric_dashboard(request, user_id):
    if request.user.id != user_id and request.user.type != "ADMIN":
        return HttpResponseForbidden("You are not allowed to access this page.")
    context = {}
    try:
        user = User.objects.get(id=user_id, is_staff=True, groups__name="Sales")
    except User.DoesNotExist:
        return render(request, "404.html", status=404)

    context["user"] = user
    context.update(get_sales_dashboard_context(account_owner_id=user_id))
    return render(request, "dashboards/user_sales_metric_dashboard.html", context)
