import logging
from django.contrib.auth.decorators import login_required
from collections import defaultdict
from django.shortcuts import render
from django.db.models import (
    F,
    Sum,
    Avg,
    ExpressionWrapper,
    DecimalField,
    FloatField,
    Case,
    When,
    Value,
    CharField,
    Count,
    Func,
    Q,
    Subquery,
    OuterRef,
)
from django.http import JsonResponse
from django.db.models.functions import (
    ExtractYear,
    Coalesce,
    Round,
    TruncMonth,
    TruncDay,
    Abs,
)
from django.core.paginator import Paginator
from django.utils import timezone
from decimal import Decimal
from datetime import datetime as dt, timedelta
from api.models import *
from api.models.seller.seller import *
from api.models.order.order import *
from api.models.order.order_group import *
from api.models.order.order_line_item import *
from api.models.user.user_group import *
import requests
import json
import csv
from django.http import HttpResponse

logger = logging.getLogger(__name__)


def index(request):
    return render(request, "dashboards/index.html")


def sales_dashboard(request):
    context = get_sales_dashboard_context()
    return render(request, "dashboards/sales_dashboard.html", context)


def get_sales_dashboard_context():
    context = {}
    date_range_start_date = dt(2024, 1, 1)
    date_range_end_date = dt(2024, 12, 31)
    delta_month = timezone.now() - timedelta(days=30)

    ##GMV##
    # customer Amount Completed
    customer_amounts = Order.objects.annotate(
        customer_amount_completed=Sum(
            Case(
                When(
                    Q(status="COMPLETE")
                    & ~Q(order_line_items__stripe_invoice_line_item_id="BYPASS")
                    & ~Q(order_line_items__rate=0),
                    then=ExpressionWrapper(
                        F("order_line_items__rate")
                        * F("order_line_items__quantity")
                        * (1 + F("order_line_items__platform_fee_percent") * 0.01),
                        output_field=DecimalField(),
                    ),
                ),
                default=Value(0),
                output_field=DecimalField(),
            )
        ),
        customer_amount=Sum(
            ExpressionWrapper(
                F("order_line_items__rate")
                * F("order_line_items__quantity")
                * (1 + F("order_line_items__platform_fee_percent") * 0.01),
                output_field=DecimalField(),
            ),
            filter=~Q(order_line_items__stripe_invoice_line_item_id="BYPASS")
            & ~Q(order_line_items__rate=0),
        ),
    ).aggregate(
        total_completed=Sum("customer_amount_completed"), total=Sum("customer_amount")
    )

    customer_amount_completed = customer_amounts["total_completed"] or Decimal("0.00")
    customer_amount = customer_amounts["total"] or Decimal("0.00")

    context["customer_amount_completed"] = customer_amount_completed
    context["customer_amount"] = customer_amount

    ##Net Revenue##
    # Supplier Amount Complete
    supplier_amounts = Order.objects.annotate(
        supplier_amount_complete=Sum(
            Case(
                When(
                    Q(status="COMPLETE")
                    & ~Q(order_line_items__stripe_invoice_line_item_id="BYPASS")
                    & ~Q(order_line_items__rate=0),
                    then=F("order_line_items__rate") * F("order_line_items__quantity"),
                ),
                default=Value(0),
                output_field=DecimalField(),
            )
        ),
        supplier_amount=Sum(
            F("order_line_items__rate") * F("order_line_items__quantity"),
            output_field=DecimalField(),
            filter=~Q(order_line_items__stripe_invoice_line_item_id="BYPASS")
            & ~Q(order_line_items__rate=0),
        ),
    ).aggregate(
        total_complete=Sum("supplier_amount_complete"),
        total=Sum("supplier_amount"),
        total_scheduled=Sum(
            Case(
                When(
                    Q(status="SCHEDULED")
                    & ~Q(order_line_items__stripe_invoice_line_item_id="BYPASS")
                    & ~Q(order_line_items__rate=0),
                    then=F("order_line_items__rate") * F("order_line_items__quantity"),
                ),
                default=Value(0),
                output_field=DecimalField(),
            )
        ),
    )

    supplier_amount_complete = supplier_amounts["total_complete"] or Decimal("0.00")
    supplier_amount_scheduled = supplier_amounts["total_scheduled"] or Decimal("0.00")
    supplier_amount = supplier_amounts["total"] or Decimal("0.00")

    context["supplier_amount_scheduled"] = supplier_amount_scheduled
    context["supplier_amount_complete"] = supplier_amount_complete
    context["supplier_amount"] = supplier_amount

    # Net Revenue Measures
    net_revenue_completed = customer_amount_completed - supplier_amount_complete
    context["net_revenue_completed"] = net_revenue_completed
    net_revenue = customer_amount - supplier_amount
    context["net_revenue"] = net_revenue
    ##AOV##
    # Average Order Value
    average_order_value = Order.objects.annotate(
        order_value=Sum(
            F("order_line_items__rate")
            * F("order_line_items__quantity")
            * (1 + F("order_line_items__platform_fee_percent") * 0.01),
            output_field=DecimalField(),
            filter=~Q(order_line_items__stripe_invoice_line_item_id="BYPASS")
            & ~Q(order_line_items__rate=0),
        )
    ).aggregate(average=Avg("order_value"))["average"] or Decimal("0.00")
    context["average_order_value"] = average_order_value

    ##Take Rate##
    # Take Rate
    take_rate = (
        (customer_amount - supplier_amount) / customer_amount
        if customer_amount != 0
        else Decimal("0.00")
    )
    take_rate_static = take_rate * 100
    context["take_rate_static"] = take_rate_static
    context["take_rate"] = take_rate

    ##Total Users##
    # Total Users
    total_users = OrderGroup.objects.values("user_id").distinct().count()
    context["total_users"] = total_users

    ##Total Companies##
    total_companies = UserGroup.objects.values("name").distinct().count()
    context["total_companies"] = total_companies

    ##Total Sellers##
    total_sellers = (
        OrderGroup.objects.values("seller_product_seller_location__id")
        .distinct()
        .count()
    )
    context["total_sellers"] = total_sellers

    ##Total Listings##
    total_listings = OrderGroup.objects.values(
        "seller_product_seller_location__id"
    ).count()
    context["total_listings"] = total_listings

    ##Graphs##
    # GMV by Month Graph
    gmv_by_month = (
        Order.objects.filter(
            Q(status="COMPLETE") | Q(status="SCHEDULED"),
            end_date__range=[date_range_start_date, date_range_end_date],
        )
        .annotate(month=TruncMonth("end_date"))
        .values("month")
        .annotate(
            total_customer_amount_completed=Sum(
                Case(
                    When(
                        Q(status="COMPLETE")
                        & ~Q(order_line_items__stripe_invoice_line_item_id="BYPASS")
                        & ~Q(order_line_items__rate=0),
                        then=F("order_line_items__rate")
                        * F("order_line_items__quantity")
                        * (1 + F("order_line_items__platform_fee_percent") * 0.01),
                    ),
                    default=Value(0),
                    output_field=DecimalField(),
                )
            ),
            total_customer_amount_scheduled=Sum(
                Case(
                    When(
                        Q(status="SCHEDULED")
                        & ~Q(order_line_items__stripe_invoice_line_item_id="BYPASS")
                        & ~Q(order_line_items__rate=0),
                        then=F("order_line_items__rate")
                        * F("order_line_items__quantity")
                        * (1 + F("order_line_items__platform_fee_percent") * 0.01),
                    ),
                    default=Value(0),
                    output_field=DecimalField(),
                )
            ),
        )
        .order_by("month")
    )

    # Prepare data for chart.js
    chart_labels = [entry["month"].strftime("%Y-%m") for entry in gmv_by_month]
    chart_data_completed = [
        float(entry["total_customer_amount_completed"]) for entry in gmv_by_month
    ]
    chart_data_scheduled = [
        float(entry["total_customer_amount_scheduled"]) for entry in gmv_by_month
    ]

    context["gmv_by_month_labels"] = json.dumps(chart_labels)
    context["gmv_by_month_data_completed"] = json.dumps(chart_data_completed)
    context["gmv_by_month_data_scheduled"] = json.dumps(chart_data_scheduled)

    # Net Revenue by Month Graph
    net_revenue_by_month = (
        Order.objects.filter(
            Q(status="COMPLETE") | Q(status="SCHEDULED"),
            end_date__range=[date_range_start_date, date_range_end_date],
        )
        .annotate(month=TruncMonth("end_date"))
        .values("month")
        .annotate(
            total_customer_amount_completed=Sum(
                Case(
                    When(
                        Q(status="COMPLETE")
                        & ~Q(order_line_items__stripe_invoice_line_item_id="BYPASS")
                        & ~Q(order_line_items__rate=0),
                        then=F("order_line_items__rate")
                        * F("order_line_items__quantity")
                        * (1 + F("order_line_items__platform_fee_percent") * 0.01),
                    ),
                    default=Value(0),
                    output_field=DecimalField(),
                )
            ),
            total_supplier_amount_completed=Sum(
                Case(
                    When(
                        Q(status="COMPLETE")
                        & ~Q(order_line_items__stripe_invoice_line_item_id="BYPASS")
                        & ~Q(order_line_items__rate=0),
                        then=F("order_line_items__rate")
                        * F("order_line_items__quantity"),
                    ),
                    default=Value(0),
                    output_field=DecimalField(),
                )
            ),
            total_customer_amount_scheduled=Sum(
                Case(
                    When(
                        Q(status="SCHEDULED")
                        & ~Q(order_line_items__stripe_invoice_line_item_id="BYPASS")
                        & ~Q(order_line_items__rate=0),
                        then=F("order_line_items__rate")
                        * F("order_line_items__quantity")
                        * (1 + F("order_line_items__platform_fee_percent") * 0.01),
                    ),
                    default=Value(0),
                    output_field=DecimalField(),
                )
            ),
            total_supplier_amount_scheduled=Sum(
                Case(
                    When(
                        Q(status="SCHEDULED")
                        & ~Q(order_line_items__stripe_invoice_line_item_id="BYPASS")
                        & ~Q(order_line_items__rate=0),
                        then=F("order_line_items__rate")
                        * F("order_line_items__quantity"),
                    ),
                    default=Value(0),
                    output_field=DecimalField(),
                )
            ),
        )
        .order_by("month")
    )

    # Calculate net revenue for each month
    net_revenue_by_month_data = [
        {
            "month": entry["month"],
            "net_revenue_completed": entry["total_customer_amount_completed"]
            - entry["total_supplier_amount_completed"],
            "net_revenue_scheduled": entry["total_customer_amount_scheduled"]
            - entry["total_supplier_amount_scheduled"],
        }
        for entry in net_revenue_by_month
    ]

    # Prepare data for chart.js
    net_revenue_labels = [
        entry["month"].strftime("%Y-%m") for entry in net_revenue_by_month_data
    ]
    net_revenue_data = [
        float(entry["net_revenue_completed"]) for entry in net_revenue_by_month_data
    ]
    net_revenue_scheduled_data = [
        float(entry["net_revenue_scheduled"]) for entry in net_revenue_by_month_data
    ]

    context["net_revenue_by_month_labels"] = json.dumps(net_revenue_labels)
    context["net_revenue_by_month_data"] = json.dumps(net_revenue_data)
    context["net_revenue_scheduled_data"] = json.dumps(net_revenue_scheduled_data)

    ##Daily GMV Rate for the Past Month##
    daily_gmv_rate = (
        Order.objects.filter(
            Q(status="COMPLETE") | Q(status="SCHEDULED"),
            end_date__range=[delta_month, timezone.now().replace(tzinfo=None)],
        )
        .annotate(day=TruncDay("end_date"))
        .values("day")
        .annotate(
            total_customer_amount_completed=Sum(
                Case(
                    When(
                        Q(status="COMPLETE")
                        & ~Q(order_line_items__stripe_invoice_line_item_id="BYPASS")
                        & ~Q(order_line_items__rate=0),
                        then=F("order_line_items__rate")
                        * F("order_line_items__quantity")
                        * (1 + F("order_line_items__platform_fee_percent") * 0.01),
                    ),
                    default=Value(0),
                    output_field=DecimalField(),
                )
            ),
        )
        .order_by("day")
    )

    # Prepare data for chart.js
    daily_gmv_labels = [entry["day"].strftime("%Y-%m-%d") for entry in daily_gmv_rate]
    daily_gmv_data_completed = [
        float(entry["total_customer_amount_completed"]) for entry in daily_gmv_rate
    ]

    context["daily_gmv_labels"] = json.dumps(daily_gmv_labels)
    context["daily_gmv_data_completed"] = json.dumps(daily_gmv_data_completed)

    ##Take Rate by Month Graph##
    take_rate_by_month = (
        Order.objects.filter(
            Q(status="COMPLETE") | Q(status="SCHEDULED"),
            end_date__range=[
                date_range_start_date,
                min(date_range_end_date, timezone.now().replace(tzinfo=None)),
            ],
        )
        .annotate(month=TruncMonth("end_date"))
        .values("month")
        .annotate(
            total_customer_amount_completed=Sum(
                Case(
                    When(
                        Q(status="COMPLETE")
                        & ~Q(order_line_items__stripe_invoice_line_item_id="BYPASS")
                        & ~Q(order_line_items__rate=0),
                        then=F("order_line_items__rate")
                        * F("order_line_items__quantity")
                        * (1 + F("order_line_items__platform_fee_percent") * 0.01),
                    ),
                    default=Value(0),
                    output_field=DecimalField(),
                )
            ),
            total_supplier_amount_completed=Sum(
                Case(
                    When(
                        Q(status="COMPLETE")
                        & ~Q(order_line_items__stripe_invoice_line_item_id="BYPASS")
                        & ~Q(order_line_items__rate=0),
                        then=F("order_line_items__rate")
                        * F("order_line_items__quantity"),
                    ),
                    default=Value(0),
                    output_field=DecimalField(),
                )
            ),
        )
        .order_by("month")
    )

    # Calculate take rate for each month
    take_rate_by_month_data = [
        {
            "month": entry["month"],
            "take_rate": (
                (
                    entry["total_customer_amount_completed"]
                    - entry["total_supplier_amount_completed"]
                )
                / entry["total_customer_amount_completed"]
                * 100
                if entry["total_customer_amount_completed"] != 0
                else Decimal("0.00")
            ),
        }
        for entry in take_rate_by_month
    ]

    # Prepare data for chart.js
    take_rate_labels = [
        entry["month"].strftime("%Y-%m") for entry in take_rate_by_month_data
    ]
    take_rate_data = [float(entry["take_rate"]) for entry in take_rate_by_month_data]

    context["take_rate_by_month_labels"] = json.dumps(take_rate_labels)
    context["take_rate_by_month_data"] = json.dumps(take_rate_data)

    ##Daily Net Revenue Rate for the Past Month##
    daily_net_revenue_rate = (
        Order.objects.filter(
            Q(status="COMPLETE") | Q(status="SCHEDULED"),
            end_date__range=[delta_month, timezone.now().replace(tzinfo=None)],
        )
        .annotate(day=TruncDay("end_date"))
        .values("day")
        .annotate(
            total_customer_amount_completed=Sum(
                Case(
                    When(
                        Q(status="COMPLETE")
                        & ~Q(order_line_items__stripe_invoice_line_item_id="BYPASS")
                        & ~Q(order_line_items__rate=0),
                        then=F("order_line_items__rate")
                        * F("order_line_items__quantity")
                        * (1 + F("order_line_items__platform_fee_percent") * 0.01),
                    ),
                    default=Value(0),
                    output_field=DecimalField(),
                )
            ),
            total_supplier_amount_completed=Sum(
                Case(
                    When(
                        Q(status="COMPLETE")
                        & ~Q(order_line_items__stripe_invoice_line_item_id="BYPASS")
                        & ~Q(order_line_items__rate=0),
                        then=F("order_line_items__rate")
                        * F("order_line_items__quantity"),
                    ),
                    default=Value(0),
                    output_field=DecimalField(),
                )
            ),
        )
        .order_by("day")
    )

    # Calculate daily net revenue
    daily_net_revenue_data = [
        {
            "day": entry["day"],
            "net_revenue_completed": entry["total_customer_amount_completed"]
            - entry["total_supplier_amount_completed"],
        }
        for entry in daily_net_revenue_rate
    ]

    # Prepare data for chart.js
    daily_net_revenue_labels = [
        entry["day"].strftime("%Y-%m-%d") for entry in daily_net_revenue_data
    ]
    daily_net_revenue_data_completed = [
        float(entry["net_revenue_completed"]) for entry in daily_net_revenue_data
    ]

    context["daily_net_revenue_labels"] = json.dumps(daily_net_revenue_labels)
    context["daily_net_revenue_data_completed"] = json.dumps(
        daily_net_revenue_data_completed
    )

    return context


def export_sales_dashboard_csv(request):
    # Gather ctx data from sales dashboard
    context = get_sales_dashboard_context()

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="sales_dashboard.csv"'

    writer = csv.writer(response)
    writer.writerow(["Metric", "Value"])

    # Write data to CSV
    writer.writerow(["Customer Amount Completed", context["customer_amount_completed"]])
    writer.writerow(["Customer Amount", context["customer_amount"]])
    writer.writerow(["Supplier Amount Scheduled", context["supplier_amount_scheduled"]])
    writer.writerow(["Supplier Amount Completed", context["supplier_amount_complete"]])
    writer.writerow(["Supplier Amount", context["supplier_amount"]])
    writer.writerow(["Net Revenue Completed", context["net_revenue_completed"]])
    writer.writerow(["Net Revenue", context["net_revenue"]])
    writer.writerow(["Average Order Value", context["average_order_value"]])
    writer.writerow(["Take Rate Static", context["take_rate_static"]])
    writer.writerow(["Take Rate", context["take_rate"]])
    writer.writerow(["Total Users", context["total_users"]])
    writer.writerow(["Total Companies", context["total_companies"]])
    writer.writerow(["Total Sellers", context["total_sellers"]])
    writer.writerow(["Total Listings", context["total_listings"]])

    # Write GMV by Month data
    writer.writerow([])
    writer.writerow(["GMV by Month"])
    writer.writerow(["Month", "Completed", "Scheduled"])
    for month, completed, scheduled in zip(
        json.loads(context["gmv_by_month_labels"]),
        json.loads(context["gmv_by_month_data_completed"]),
        json.loads(context["gmv_by_month_data_scheduled"]),
    ):
        writer.writerow([month, completed, scheduled])

    # Write Net Revenue by Month data
    writer.writerow([])
    writer.writerow(["Net Revenue by Month"])
    writer.writerow(["Month", "Completed", "Scheduled"])
    for month, completed, scheduled in zip(
        json.loads(context["net_revenue_by_month_labels"]),
        json.loads(context["net_revenue_by_month_data"]),
        json.loads(context["net_revenue_scheduled_data"]),
    ):
        writer.writerow([month, completed, scheduled])

    # Write Daily GMV Rate data
    writer.writerow([])
    writer.writerow(["Daily GMV Rate"])
    writer.writerow(["Day", "Completed"])
    for day, completed in zip(
        json.loads(context["daily_gmv_labels"]),
        json.loads(context["daily_gmv_data_completed"]),
    ):
        writer.writerow([day, completed])

    # Write Take Rate by Month data
    writer.writerow([])
    writer.writerow(["Take Rate by Month"])
    writer.writerow(["Month", "Take Rate"])
    for month, take_rate in zip(
        json.loads(context["take_rate_by_month_labels"]),
        json.loads(context["take_rate_by_month_data"]),
    ):
        writer.writerow([month, take_rate])

    # Write Daily Net Revenue Rate data
    writer.writerow([])
    writer.writerow(["Daily Net Revenue Rate"])
    writer.writerow(["Day", "Completed"])
    for day, completed in zip(
        json.loads(context["daily_net_revenue_labels"]),
        json.loads(context["daily_net_revenue_data_completed"]),
    ):
        writer.writerow([day, completed])

    # Write Order data associated with customer_amount_completed
    writer.writerow([])
    writer.writerow(["Orders Associated with Customer Amount Completed"])
    writer.writerow(
        [
            "Order ID",
            "Customer Amount Completed",
            "Net Revenue Completed",
            "Order Date",
            "Status",
        ]
    )

    orders = Order.objects.annotate(
        customer_amount_completed=Sum(
            Case(
                When(
                    Q(status="COMPLETE")
                    & ~Q(order_line_items__stripe_invoice_line_item_id="BYPASS")
                    & ~Q(order_line_items__rate=0),
                    then=ExpressionWrapper(
                        F("order_line_items__rate")
                        * F("order_line_items__quantity")
                        * (1 + F("order_line_items__platform_fee_percent") * 0.01),
                        output_field=DecimalField(),
                    ),
                ),
                default=Value(0),
                output_field=DecimalField(),
            )
        ),
        supplier_amount_complete=Sum(
            Case(
                When(
                    Q(status="COMPLETE")
                    & ~Q(order_line_items__stripe_invoice_line_item_id="BYPASS")
                    & ~Q(order_line_items__rate=0),
                    then=F("order_line_items__rate") * F("order_line_items__quantity"),
                ),
                default=Value(0),
                output_field=DecimalField(),
            )
        ),
    ).filter(customer_amount_completed__gt=0)

    for order in orders:
        net_revenue_completed = (
            order.customer_amount_completed - order.supplier_amount_complete
        )
        writer.writerow(
            [
                order.id,
                order.customer_amount_completed,
                net_revenue_completed,
                order.end_date.strftime("%Y-%m-%d"),
                order.status,
            ]
        )
    # Calculate totals for customer_amount_completed and net_revenue_completed
    total_customer_amount_completed = sum(
        order.customer_amount_completed for order in orders
    )
    total_net_revenue_completed = sum(
        order.customer_amount_completed - order.supplier_amount_complete
        for order in orders
    )

    # Write totals to CSV
    writer.writerow([])
    writer.writerow(
        ["Total", total_customer_amount_completed, total_net_revenue_completed]
    )
    return response


def payout_reconciliation(request):
    context = {}
    order_count = Order.objects.count()
    print(f"Order Count: {order_count}")

    # Subqueries to aggregate related fields
    # main_product_name_subquery = Subquery(
    #     Product.objects.filter(
    #         id=OuterRef('order_group__seller_product_seller_location__seller_product__product__main_product__id')
    #     ).values('main_product__name')[:1]
    # )

    seller_location_names_subquery = Subquery(
        SellerLocation.objects.filter(
            id=OuterRef(
                "order_group__seller_product_seller_location__seller_location__id"
            )
        ).values("name")[:1]
    )

    user_address_subquery = Subquery(
        UserAddress.objects.filter(id=OuterRef("order_group__user_address__id")).values(
            "name"
        )[:1]
    )

    orderRelations = (
        Order.objects.annotate(
            main_product_name=F(
                "order_group__seller_product_seller_location__seller_product__product__main_product__name"
            ),
            seller_location_names=seller_location_names_subquery,
            user_address=user_address_subquery,
            end_date_annotate=F("end_date"),
            supplier_amount=ExpressionWrapper(
                Round(F("order_line_items__rate") * F("order_line_items__quantity"), 2),
                output_field=DecimalField(decimal_places=2),
            ),
            seller_invoice_amount=Coalesce(
                F("seller_invoice_payable_line_items__amount"),
                Value(0),
                output_field=DecimalField(decimal_places=2),
            ),
            payout_amount=Coalesce(
                F("payouts__amount"),
                Value(0),
                output_field=DecimalField(decimal_places=2),
            ),
            abs_difference=ExpressionWrapper(
                Abs(F("seller_invoice_amount") - F("supplier_amount")),
                output_field=FloatField(),
            ),
            reconcil_status=Case(
                When(
                    seller_invoice_amount=F("supplier_amount"), then=Value("Reconciled")
                ),
                default=Value("Not Reconciled"),
                output_field=CharField(),
            ),
            order_status=Case(
                When(payout_amount__isnull=True, then=Value("Unpaid")),
                When(
                    Q(seller_invoice_amount__isnull=True)
                    & Q(payout_amount=F("seller_invoice_amount")),
                    then=Value("Paid"),
                ),
                When(
                    Q(payout_amount__gte=F("seller_invoice_amount")), then=Value("Paid")
                ),
                default=Value("Unpaid"),
            ),
            order_status_comb=Func(
                F("order_status"),
                Value(", "),
                F("reconcil_status"),
                function="CONCAT",
                output_field=CharField(),
            ),
            order_url_annotate=Func(
                Value(settings.DASHBOARD_BASE_URL + "/"),
                Value("admin/api/order/"),
                F("id"),
                Value("/change/"),
                function="CONCAT",
                output_field=CharField(),
            ),
        )
        .distinct("id")
        .values(
            "id",
            "main_product_name",
            "seller_location_names",
            "user_address",
            "end_date_annotate",
            "supplier_amount",
            "seller_invoice_amount",
            "payout_amount",
            "reconcil_status",
            "order_status",
            "order_status_comb",
            "order_url_annotate",
        )
    )

    unique_order_status_comb = set(
        order["order_status_comb"] for order in orderRelations
    )
    total_seller_invoice_amount = sum(
        float(order["seller_invoice_amount"] or 0) for order in orderRelations
    )
    context["total_seller_invoice_amount"] = total_seller_invoice_amount

    # Group by month and sum seller_invoice_amount for each order_status_comb
    monthly_data = defaultdict(lambda: defaultdict(float))
    for order in orderRelations:
        order_date = order["end_date_annotate"]
        month = order_date.strftime("%Y-%m")  # Format as YYYY-MM
        seller_invoice_amount = (
            order["seller_invoice_amount"] or 0
        )  # Replace None with 0
        order_status_comb = order["order_status_comb"]
        monthly_data[month][order_status_comb] += float(seller_invoice_amount)

    sorted_monthly_data = {
        month: dict(status_data) for month, status_data in sorted(monthly_data.items())
    }

    # Prep for chart.js
    chart_data = {"labels": list(sorted_monthly_data.keys()), "datasets": []}

    # Define colors for each status
    status_colors = {
        "Paid, Reconciled": "rgba(75, 192, 192, 0.2)",
        "Paid, Not Reconciled": "rgba(255, 206, 86, 0.2)",
        "Unpaid, Reconciled": "rgba(153, 102, 255, 0.2)",
        "Unpaid, Not Reconciled": "rgba(255, 99, 132, 0.2)",
    }

    for status, color in status_colors.items():
        dataset = {
            "label": status,
            "data": [
                monthly_data[month].get(status, 0) for month in chart_data["labels"]
            ],
            "backgroundColor": color,
            "borderColor": color.replace("0.2", "1"),
            "borderWidth": 1,
        }
        chart_data["datasets"].append(dataset)

    # Convert to json
    chart_data_json = json.dumps(chart_data)

    context["chart_data"] = chart_data_json
    context["orderRelations"] = orderRelations
    paginator = Paginator(orderRelations, 30)  # Show 30 orders per page

    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    context["page_obj"] = page_obj

    context["unique_order_status_comb"] = unique_order_status_comb
    return render(request, "dashboards/payout_reconciliation.html", context)


@login_required(login_url="/admin/login/")
def command_center(request):
    return render(
        request,
        "dashboards/index.html",
    )

def all_orders_dashboard(request):
    context = {}
    orders = Order.objects.annotate(
        order_id=F("id"),
        annotated_order_group_id=F("order_group__id"),
        order_created_date=F("created_on"),
        order_start_date=F("start_date"),
        usergroup_name=F("order_group__user__user_group__name"),
        useraddress_id=F("order_group__user_address__id"),
        useraddress_name=F("order_group__user_address__name"),
        user_first_name=F("order_group__user__first_name"),
        user_last_name=F("order_group__user__last_name"),
        user_email=F("order_group__user__email"),
        order_status=F("status"),
        sellerlocation_name=F("order_group__seller_product_seller_location__seller_location__name"),
        mainproduct_name=F("order_group__seller_product_seller_location__seller_product__product__main_product__name"),
    ).values(
        "order_id",
        "order_group_id",
        "order_created_date",
        "order_start_date",
        "usergroup_name",
        "useraddress_id",
        "useraddress_name",
        "user_first_name",
        "user_last_name",
        "user_email",
        "order_status",
        "sellerlocation_name",
        "mainproduct_name",
    )
    context["orders"] = orders
    return render(
        request,
        "dashboards/all_orders_dashboard.html",
        context,
    )