
import logging
from django.contrib.auth.decorators import login_required
from django.forms import FloatField
from django.db.models import DateField
from django.shortcuts import render
from django.db.models import (
    F,
    Sum,
    Avg,
    ExpressionWrapper,
    DecimalField,
    Case,
    When,
    Value,
    CharField,
    FloatField,
    Count,
    Q,
    Subquery,
    OuterRef,
    Max,
    BooleanField,
    Func,
)
from django.db.models import F, ExpressionWrapper, FloatField
from django.db.models.functions import Cast, Extract
from django.utils import timezone
from django.utils.timezone import now
from decimal import Decimal
from datetime import timedelta
from api.models import *
from api.models.seller.seller import *
from api.models.order.order import *
from api.models.order.order_group import *
from api.models.order.order_line_item import *
from api.models.user.user_group import *
import json
from django.db.models.functions import TruncMonth, TruncDay
from django.conf import settings
from django.db.models import DurationField

def seller_location_dashboard(request):
    context = {}
    unique_seller_locations_count = (
        SellerLocation.objects.values("id").distinct().count()
    )

    # Get the current month and the previous month
    current_month = timezone.now().replace(day=1)
    previous_month = (current_month - timedelta(days=1)).replace(day=1)

    # Count seller locations for the current month
    current_month_seller_locations = SellerLocation.objects.filter(
        created_on__gte=current_month
    ).count()

    # Count seller locations for the previous month
    previous_month_seller_locations = SellerLocation.objects.filter(
        created_on__gte=previous_month, created_on__lt=current_month
    ).count()

    # Calculate the percentage change
    if previous_month_seller_locations > 0:
        percent_change = (
            (current_month_seller_locations - previous_month_seller_locations)
            / previous_month_seller_locations
        ) * 100
    else:
        percent_change = 100.0 if current_month_seller_locations > 0 else 0.0

    # Calculate the number of seller locations with processed orders in the last 28 days
    last_28_days = timezone.now() - timedelta(days=28)
    seller_locations_with_processed_orders = (
        SellerLocation.objects.filter(
            seller_product_seller_locations__order_groups__orders__status="COMPLETE",
            seller_product_seller_locations__order_groups__orders__end_date__gte=last_28_days,
        )
        .distinct()
        .count()
    )

    # Calculate revenue generated by each seller location
    seller_location_revenue = SellerLocation.objects.annotate(
        revenue=Sum(
            Case(
                When(
                    seller_product_seller_locations__order_groups__orders__status="COMPLETE",
                    then=F(
                        "seller_product_seller_locations__order_groups__orders__order_line_items__rate"
                    )
                    * F(
                        "seller_product_seller_locations__order_groups__orders__order_line_items__quantity"
                    ),
                ),
                default=Value(0),
                output_field=DecimalField(),
            )
        )
    )

    # Calculate the average revenue
    total_revenue = sum(location.revenue for location in seller_location_revenue)
    average_revenue = (
        total_revenue / len(seller_location_revenue)
        if seller_location_revenue
        else Decimal("0.00")
    )

    # Calculate the count of seller locations by month for the past year
    one_year_ago = timezone.now() - timedelta(days=365)
    seller_locations_by_month = (
        SellerLocation.objects.filter(created_on__gte=one_year_ago)
        .annotate(month=TruncMonth("created_on"))
        .values("month")
        .annotate(count=Count("id"))
        .order_by("month")
    )

    # Prepare data for chart.js
    chart_labels = [
        entry["month"].strftime("%b-%Y") for entry in seller_locations_by_month
    ]
    chart_data = [entry["count"] for entry in seller_locations_by_month]

    context["seller_locations_by_month_labels"] = json.dumps(chart_labels)
    context["seller_locations_by_month_data"] = json.dumps(chart_data)

    # Calculate the average revenue per seller location by month for the past year
    avg_revenue_per_seller_location_by_month = (
        SellerLocation.objects.filter(created_on__gte=one_year_ago)
        .annotate(month=TruncMonth("created_on"))
        .values("month")
        .annotate(
            avg_revenue=Avg(
                Case(
                    When(
                        seller_product_seller_locations__order_groups__orders__status="COMPLETE",
                        then=F(
                            "seller_product_seller_locations__order_groups__orders__order_line_items__rate"
                        )
                        * F(
                            "seller_product_seller_locations__order_groups__orders__order_line_items__quantity"
                        ),
                    ),
                    default=Value(0),
                    output_field=DecimalField(),
                )
            )
        )
        .order_by("month")
    )

    # Prepare data for chart.js
    avg_revenue_chart_labels = [
        entry["month"].strftime("%b-%Y")
        for entry in avg_revenue_per_seller_location_by_month
    ]
    avg_revenue_chart_data = [
        float(entry["avg_revenue"])
        for entry in avg_revenue_per_seller_location_by_month
    ]

    context["avg_revenue_per_seller_location_by_month_labels"] = json.dumps(
        avg_revenue_chart_labels
    )
    context["avg_revenue_per_seller_location_by_month_data"] = json.dumps(
        avg_revenue_chart_data
    )

    context["average_revenue_per_seller_location"] = average_revenue
    context["seller_locations_with_processed_orders"] = (
        seller_locations_with_processed_orders
    )
    context["percent_change_seller_locations"] = percent_change
    context["unique_seller_locations_count"] = unique_seller_locations_count
    return render(
        request,
        "dashboards/seller_location_dashboard.html",
        context,
    )


def users_dashboard(request):
    context = {}
    total_users = User.objects.values("id").distinct().count()

    # Get the current month and the previous month
    current_month = timezone.now().replace(day=1)
    previous_month = (current_month - timedelta(days=1)).replace(day=1)

    # Count users for the current month
    current_month_users = User.objects.filter(date_joined__gte=current_month).count()

    # Count users for the previous month
    previous_month_users = User.objects.filter(
        date_joined__gte=previous_month, date_joined__lt=current_month
    ).count()

    # Calculate the percentage change
    if previous_month_users > 0:
        percent_change_users = (
            (current_month_users - previous_month_users) / previous_month_users
        ) * 100
    else:
        percent_change_users = 100.0 if current_month_users > 0 else 0.0

    # Calculate the number of users who have placed an order in the last 28 days
    last_28_days = timezone.now() - timedelta(days=28)
    users_with_orders_last_28_days = (
        User.objects.filter(
            useraddress__order_groups__orders__end_date__gte=last_28_days
        )
        .distinct()
        .count()
    )

    # Calculate the average order value for active users (users who have placed an order in the last 28 days)
    average_order_value_per_active_user = Order.objects.filter(
        order_group__user__in=User.objects.filter(
            useraddress__order_groups__orders__end_date__gte=last_28_days
        )
    ).annotate(
        order_value=Sum(
            F("order_line_items__rate")
            * F("order_line_items__quantity")
            * (1 + F("order_line_items__platform_fee_percent") * 0.01),
            output_field=DecimalField(),
            filter=~Q(order_line_items__stripe_invoice_line_item_id="BYPASS")
            & ~Q(order_line_items__rate=0),
        )
    ).aggregate(
        average=Avg("order_value")
    )[
        "average"
    ] or Decimal(
        "0.00"
    )

    # Calculate the number of users created each month for the past year
    one_year_ago = timezone.now() - timedelta(days=365)
    users_by_month = (
        User.objects.filter(date_joined__gte=one_year_ago)
        .annotate(month=TruncMonth("date_joined"))
        .values("month")
        .annotate(count=Count("id"))
        .order_by("month")
    )

    # Prepare data for chart.js
    user_chart_labels = [entry["month"].strftime("%b-%Y") for entry in users_by_month]
    user_chart_data = [entry["count"] for entry in users_by_month]

    context["user_chart_labels"] = json.dumps(user_chart_labels)
    context["user_chart_data"] = json.dumps(user_chart_data)

    # Calculate the average order value per user by month for the past year
    avg_order_value_per_user_by_month = (
        Order.objects.filter(
            order_group__user__in=User.objects.filter(
                useraddress__order_groups__orders__end_date__gte=last_28_days
            )
        )
        .annotate(month=TruncMonth("order_group__user__date_joined"))
        .values("month")
        .annotate(
            avg_order_value=Avg(
                Case(
                    When(
                        ~Q(order_line_items__stripe_invoice_line_item_id="BYPASS")
                        & ~Q(order_line_items__rate=0),
                        then=F("order_line_items__rate")
                        * F("order_line_items__quantity")
                        * (1 + F("order_line_items__platform_fee_percent") * 0.01),
                    ),
                    default=Value(0),
                    output_field=DecimalField(),
                )
            )
        )
        .order_by("month")
    )

    # Prepare data for chart.js
    avg_order_value_chart_labels = [
        entry["month"].strftime("%b-%Y") for entry in avg_order_value_per_user_by_month
    ]
    avg_order_value_chart_data = [
        float(entry["avg_order_value"]) for entry in avg_order_value_per_user_by_month
    ]

    context["avg_order_value_per_user_by_month_labels"] = json.dumps(
        avg_order_value_chart_labels
    )
    context["avg_order_value_per_user_by_month_data"] = json.dumps(
        avg_order_value_chart_data
    )

    context["average_order_value_per_user"] = average_order_value_per_active_user

    context["users_with_orders_last_28_days"] = users_with_orders_last_28_days

    context["montly_percent_change_users"] = percent_change_users

    context["total_users"] = total_users
    return render(request, "dashboards/users_dashboard.html", context)


def user_groups_dashboard(request):
    context = {}
    total_user_groups = UserGroup.objects.values("name").distinct().count()

    # Get the current month and the previous month
    current_month = timezone.now().replace(day=1)
    previous_month = (current_month - timedelta(days=1)).replace(day=1)

    # Count user groups for the current month
    current_month_user_groups = UserGroup.objects.filter(
        created_on__gte=current_month
    ).count()

    # Count user groups for the previous month
    previous_month_user_groups = UserGroup.objects.filter(
        created_on__gte=previous_month, created_on__lt=current_month
    ).count()

    # Calculate the percentage change
    if previous_month_user_groups > 0:
        percent_change_user_groups = (
            (current_month_user_groups - previous_month_user_groups)
            / previous_month_user_groups
        ) * 100
    else:
        percent_change_user_groups = 100.0 if current_month_user_groups > 0 else 0.0

    # Calculate the number of active user groups (user groups with orders in the last 28 days)
    last_28_days = timezone.now() - timedelta(days=28)
    active_user_groups = (
        UserGroup.objects.filter(
            users__useraddress__order_groups__orders__end_date__gte=last_28_days
        )
        .distinct()
        .count()
    )

    # Calculate the average spend per user group
    average_spend_per_active_user_group = UserGroup.objects.filter(
        users__useraddress__order_groups__orders__end_date__gte=last_28_days
    ).annotate(
        total_spend=Sum(
            Case(
                When(
                    users__useraddress__order_groups__orders__status="COMPLETE",
                    then=F(
                        "users__useraddress__order_groups__orders__order_line_items__rate"
                    )
                    * F(
                        "users__useraddress__order_groups__orders__order_line_items__quantity"
                    )
                    * (
                        1
                        + F(
                            "users__useraddress__order_groups__orders__order_line_items__platform_fee_percent"
                        )
                        * 0.01
                    ),
                ),
                default=Value(0),
                output_field=DecimalField(),
            )
        )
    ).aggregate(
        average=Avg("total_spend")
    )[
        "average"
    ] or Decimal(
        "0.00"
    )

    # Calculate the count of user groups by month for the past year
    one_year_ago = timezone.now() - timedelta(days=365)
    user_groups_by_month = (
        UserGroup.objects.filter(created_on__gte=one_year_ago)
        .annotate(month=TruncMonth("created_on"))
        .values("month")
        .annotate(count=Count("id"))
        .order_by("month")
    )

    # Prepare data for chart.js
    user_groups_chart_labels = [
        entry["month"].strftime("%b-%Y") for entry in user_groups_by_month
    ]
    user_groups_chart_data = [entry["count"] for entry in user_groups_by_month]

    context["user_groups_chart_labels"] = json.dumps(user_groups_chart_labels)
    context["user_groups_chart_data"] = json.dumps(user_groups_chart_data)

    # Calculate the average spend per user group by month for the past year
    avg_spend_per_user_group_by_month = (
        UserGroup.objects.filter(
            users__useraddress__order_groups__orders__end_date__gte=one_year_ago
        )
        .annotate(
            month=TruncMonth("users__useraddress__order_groups__orders__end_date")
        )
        .values("month")
        .annotate(
            avg_spend=Avg(
                Case(
                    When(
                        users__useraddress__order_groups__orders__status="COMPLETE",
                        then=F(
                            "users__useraddress__order_groups__orders__order_line_items__rate"
                        )
                        * F(
                            "users__useraddress__order_groups__orders__order_line_items__quantity"
                        )
                        * (
                            1
                            + F(
                                "users__useraddress__order_groups__orders__order_line_items__platform_fee_percent"
                            )
                            * 0.01
                        ),
                    ),
                    default=Value(0),
                    output_field=DecimalField(),
                )
            )
        )
        .order_by("month")
    )

    # Filter out entries with avg_spend of 0
    avg_spend_per_user_group_by_month = [
        entry for entry in avg_spend_per_user_group_by_month if entry["avg_spend"] != 0
    ]

    # Prepare data for chart.js
    avg_spend_chart_labels = [
        entry["month"].strftime("%b-%Y") for entry in avg_spend_per_user_group_by_month
    ]
    avg_spend_chart_data = [
        float(entry["avg_spend"]) for entry in avg_spend_per_user_group_by_month
    ]

    context["avg_spend_per_user_group_by_month_labels"] = json.dumps(
        avg_spend_chart_labels
    )
    context["avg_spend_per_user_group_by_month_data"] = json.dumps(avg_spend_chart_data)
    context["average_spend_per_active_user_group"] = average_spend_per_active_user_group

    context["active_user_groups"] = active_user_groups

    context["percent_change_user_groups"] = percent_change_user_groups

    context["total_user_groups"] = total_user_groups

    return render(request, "dashboards/user_groups_dashboard.html", context)


def user_addresses_dashboard(request):
    context = {}
    total_user_addresses = UserAddress.objects.values("id").distinct().count()

    # Get the current month and the previous month
    current_month = timezone.now().replace(day=1)
    previous_month = (current_month - timedelta(days=1)).replace(day=1)

    # Count user addresses for the current month
    current_month_user_addresses = UserAddress.objects.filter(
        created_on__gte=current_month
    ).count()

    # Count user addresses for the previous month
    previous_month_user_addresses = UserAddress.objects.filter(
        created_on__gte=previous_month, created_on__lt=current_month
    ).count()

    # Calculate the percentage change
    if previous_month_user_addresses > 0:
        percent_change_user_addresses = (
            (current_month_user_addresses - previous_month_user_addresses)
            / previous_month_user_addresses
        ) * 100
    else:
        percent_change_user_addresses = (
            100.0 if current_month_user_addresses > 0 else 0.0
        )

    # Calculate the number of active user addresses (user addresses with orders in the last 28 days)
    last_28_days = timezone.now() - timedelta(days=28)
    active_user_addresses = (
        UserAddress.objects.filter(order_groups__orders__end_date__gte=last_28_days)
        .distinct()
        .count()
    )

    # Calculate the average total spend per user address
    average_spend_per_user_address = UserAddress.objects.filter(
        order_groups__orders__end_date__gte=last_28_days
    ).annotate(
        total_spend=Sum(
            Case(
                When(
                    order_groups__orders__status="COMPLETE",
                    then=F("order_groups__orders__order_line_items__rate")
                    * F("order_groups__orders__order_line_items__quantity")
                    * (
                        1
                        + F(
                            "order_groups__orders__order_line_items__platform_fee_percent"
                        )
                        * 0.01
                    ),
                ),
                default=Value(0),
                output_field=DecimalField(),
            )
        )
    ).aggregate(
        average=Avg("total_spend")
    )[
        "average"
    ] or Decimal(
        "0.00"
    )

    # Calculate the count of user addresses by month for the past year
    one_year_ago = timezone.now() - timedelta(days=365)
    user_addresses_by_month = (
        UserAddress.objects.filter(created_on__gte=one_year_ago)
        .annotate(month=TruncMonth("created_on"))
        .values("month")
        .annotate(count=Count("id"))
        .order_by("month")
    )

    # Prepare data for chart.js
    user_addresses_chart_labels = [
        entry["month"].strftime("%b-%Y") for entry in user_addresses_by_month
    ]
    user_addresses_chart_data = [entry["count"] for entry in user_addresses_by_month]

    context["user_addresses_chart_labels"] = json.dumps(user_addresses_chart_labels)
    context["user_addresses_chart_data"] = json.dumps(user_addresses_chart_data)

    # Calculate the average spend per user address by month for the past year
    avg_spend_per_user_address_by_month = (
        UserAddress.objects.filter(order_groups__orders__end_date__gte=one_year_ago)
        .annotate(month=TruncMonth("order_groups__orders__end_date"))
        .values("month")
        .annotate(
            avg_spend=Avg(
                Case(
                    When(
                        order_groups__orders__status="COMPLETE",
                        then=F("order_groups__orders__order_line_items__rate")
                        * F("order_groups__orders__order_line_items__quantity")
                        * (
                            1
                            + F(
                                "order_groups__orders__order_line_items__platform_fee_percent"
                            )
                            * 0.01
                        ),
                    ),
                    default=Value(0),
                    output_field=DecimalField(),
                )
            )
        )
        .order_by("month")
    )

    # Filter out entries with avg_spend of 0
    avg_spend_per_user_address_by_month = [
        entry
        for entry in avg_spend_per_user_address_by_month
        if entry["avg_spend"] != 0
    ]

    # Prepare data for chart.js
    avg_spend_chart_labels = [
        entry["month"].strftime("%b-%Y")
        for entry in avg_spend_per_user_address_by_month
    ]
    avg_spend_chart_data = [
        float(entry["avg_spend"]) for entry in avg_spend_per_user_address_by_month
    ]

    context["avg_spend_per_user_address_by_month_labels"] = json.dumps(
        avg_spend_chart_labels
    )
    context["avg_spend_per_user_address_by_month_data"] = json.dumps(
        avg_spend_chart_data
    )

    context["average_spend_per_user_address"] = average_spend_per_user_address

    context["active_user_addresses"] = active_user_addresses

    context["percent_change_user_addresses"] = percent_change_user_addresses

    context["total_user_addresses"] = total_user_addresses
    return render(request, "dashboards/user_addresses_dashboard.html", context)


def time_to_acceptance(request):
    context = {}
    one_month_ago = timezone.now() - timedelta(days=30)

    orders_with_time_to_acceptance = Order.objects.filter(
        accepted_on__isnull=False,
        completed_on__isnull=False,
        submitted_on__isnull=False,
        end_date__gt=one_month_ago,
        ).values(
        "id",
        "end_date",
        "accepted_on",
        "accepted_by",
        "completed_on",
        "completed_by",
        "submitted_on",
        "submitted_by",
        ).annotate(
        new_end_date=ExpressionWrapper(
            F('end_date') + timedelta(hours=15),
            output_field=DateField()
        ),
        time_to_accepted=ExpressionWrapper(
            F('accepted_on') - F('submitted_on'),
            output_field=DurationField()
        ),
        time_to_completed=ExpressionWrapper(
            F('completed_on') - F('new_end_date'),
            output_field=DurationField()
        ),
        
        ).annotate(
        time_to_accepted_hours=ExpressionWrapper(
            Cast(Extract(F('time_to_accepted'), 'epoch'), output_field=FloatField()) / 3600,
            output_field=FloatField()
        ),
        time_to_completed_hours=ExpressionWrapper(
            Cast(Extract(F('time_to_completed'), 'epoch'), output_field=FloatField()) / 3600,
            output_field=FloatField()
        )
        )

    # Calculate the average time to accepted in hours
    avg_time_to_accepted_hours = orders_with_time_to_acceptance.aggregate(
        avg_time_to_accepted=Avg("time_to_accepted_hours")
    )["avg_time_to_accepted"] or 0.0

    # Calculate the average time to completed in hours
    avg_time_to_completed_hours = orders_with_time_to_acceptance.aggregate(
        avg_time_to_completed=Avg("time_to_completed_hours")
    )["avg_time_to_completed"] or 0.0

    context["avg_time_to_accepted_hours"] = avg_time_to_accepted_hours
    context["avg_time_to_completed_hours"] = avg_time_to_completed_hours

    # Fetch user details for accepted_by, submitted_by, and completed_by
    user_ids = set(
        order['accepted_by'] for order in orders_with_time_to_acceptance
    ).union(
        order['submitted_by'] for order in orders_with_time_to_acceptance
    ).union(
        order['completed_by'] for order in orders_with_time_to_acceptance
    )

    users = User.objects.filter(id__in=user_ids).values('id', 'username')
    user_dict = {user['id']: user['username'] for user in users}

    # Add user details to the orders
    for order in orders_with_time_to_acceptance:
        order['accepted_by_username'] = user_dict.get(order['accepted_by'], 'Unknown')
        order['submitted_by_username'] = user_dict.get(order['submitted_by'], 'Unknown')
        order['completed_by_username'] = user_dict.get(order['completed_by'], 'Unknown')

    orders_count = orders_with_time_to_acceptance.count()

    # Calculate the count of orders created internally and externally by month for the past year
    orders_by_day = (
        Order.objects.filter(
            end_date__gt=one_month_ago,
            accepted_on__isnull=False,
            completed_on__isnull=False,
            submitted_on__isnull=False,
        )
        .annotate(day=TruncDay("end_date"))
        .values("day")
        .annotate(
            internal_count=Count("id", filter=Q(accepted_by__user_group_id="bd49eaab-4b46-46c0-a9bf-bace2896b795")),
            external_count=Count("id", filter=~Q(accepted_by__user_group_id="bd49eaab-4b46-46c0-a9bf-bace2896b795")),
        )
        .order_by("day")
    )

    # Prepare data for chart.js
    orders_chart_labels = [entry["day"].strftime("%d-%b-%Y") for entry in orders_by_day]  
    internal_orders_chart_data = [entry["internal_count"] for entry in orders_by_day]
    external_orders_chart_data = [entry["external_count"] for entry in orders_by_day]
    # Calculate the average time to accepted for each day
    avg_time_to_accepted_by_day = (
        orders_with_time_to_acceptance
        .values("end_date")
        .annotate(avg_time_to_accepted=Avg("time_to_accepted_hours"))
        .order_by("end_date")
    )

    # Prepare data for chart.js
    avg_time_to_accepted_chart_data = [
        entry["avg_time_to_accepted"] for entry in avg_time_to_accepted_by_day
    ]
    # Calculate the average time to completed for each day
    avg_time_to_completed_by_day = (
        orders_with_time_to_acceptance
        .values("end_date")
        .annotate(avg_time_to_completed=Avg("time_to_completed_hours"))
        .order_by("end_date")
    )

    # Prepare data for chart.js
    avg_time_to_completed_chart_data = [
        entry["avg_time_to_completed"] for entry in avg_time_to_completed_by_day
    ]

    context["avg_time_to_completed_chart_data"] = json.dumps(avg_time_to_completed_chart_data)
    context["avg_time_to_accepted_chart_data"] = json.dumps(avg_time_to_accepted_chart_data)
    context["orders_chart_labels"] = json.dumps(orders_chart_labels)
    context["internal_orders_chart_data"] = json.dumps(internal_orders_chart_data)
    context["external_orders_chart_data"] = json.dumps(external_orders_chart_data)

    context["orders_count"] = orders_count

    context["orders"] = list(orders_with_time_to_acceptance)

    return render(request, "dashboards/time_to_acceptance.html", context)