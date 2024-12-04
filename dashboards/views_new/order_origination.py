import logging

from django.contrib.auth.decorators import login_required
from django.db.models.functions import TruncMonth, TruncYear
from django.shortcuts import render

from api.models.order.order import Order

logger = logging.getLogger(__name__)


@login_required(login_url="/admin/login/")
def order_origination(request):
    # Get all Orders. Annotate the year and month of the Order.
    orders = (
        Order.objects.all()
        .annotate(
            year=TruncYear("created_on"),
            month=TruncMonth("created_on"),
        )
        .order_by("year", "month")
    )

    # Get all Orders created by is_staff Users.
    orders_by_staff_user = orders.filter(
        created_by__is_staff=True,
    )

    # Get all Order created by non-is_staff Users.
    orders_by_non_staff_user = orders.filter(
        created_by__is_staff=False,
    )

    # Get all months in the Orders data.
    year_months = orders.values("year", "month").distinct()
    # print(year_months)

    # Get count of Orders created by is_staff Users, by month.
    orders_by_staff_user_by_month_data = [
        orders_by_staff_user.filter(
            year__year=item["year"].year,
            month__month=item["month"].month,
        ).count()
        for item in year_months
    ]

    # Get count of Orders created by non-is_staff Users, by month.
    orders_by_non_staff_user_by_month_data = [
        orders_by_non_staff_user.filter(
            year=item["year"],
            month=item["month"],
        ).count()
        for item in year_months
    ]

    # Calculate the total number of orders by staff and non-staff users
    total_orders_by_staff_user = sum(orders_by_staff_user_by_month_data)
    total_orders_by_non_staff_user = sum(orders_by_non_staff_user_by_month_data)

    # Prepare data for the pie chart
    pie_chart_data = {
        "labels": ["Internally-Created Orders", "Customer-Created Orders"],
        "data": [total_orders_by_staff_user, total_orders_by_non_staff_user],
    }

    # Display the data in a chart.
    context = {}
    context["chart_labels"] = [
        f"{item['month'].month}/{item['year'].year}" for item in year_months
    ]
    context["pie_chart_data"] = pie_chart_data
    context["chart_data"] = orders_by_staff_user_by_month_data
    context["chart_scheduled"] = orders_by_non_staff_user_by_month_data

    return render(
        request,
        "dashboards/order_origination.html",
        context,
    )
