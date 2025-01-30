import logging
from datetime import datetime as dt, timedelta
from decimal import Decimal
import json
import csv
from collections import defaultdict

from django.contrib.auth.decorators import login_required
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
    Q,
    Subquery,
    OuterRef,
    Max,
    BooleanField,
)
from django.db.models import Func

from django.db.models.functions import (
    Coalesce,
    TruncMonth,
    TruncDay,
    Abs,
)
from django.db.models import Min, Exists
from django.db.models import DateField
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.timezone import now

from api.models import Order, Payout, UserGroup, OrderReview
from api_proxy import settings

logger = logging.getLogger(__name__)


def index(request):
    return render(request, "dashboards/index.html")


def sales_dashboard(request):
    context = get_sales_dashboard_context()
    return render(request, "dashboards/sales_dashboard.html", context)


def get_sales_dashboard_context(account_owner_id=None):
    context = {}
    date_range_end_date = timezone.now().replace(tzinfo=None)
    date_range_start_date = (date_range_end_date.replace(day=1) - timedelta(days=1)).replace(month=1, day=1)
    delta_month = timezone.now() - timedelta(days=30)

    if account_owner_id:
        order_filter = Q(order_group__user_address__user_group__account_owner_id=account_owner_id)
    else:
        order_filter = Q()

    print(order_filter)
    print(account_owner_id)

    ##GMV##
    # customer Amount Completed
    customer_amounts = (
        Order.objects.filter(order_filter)
        .annotate(
            customer_amount_completed=Sum(
                Case(
                    When(
                        Q(status="COMPLETE")
                        & ~Q(order_line_items__rate=0)
                        & ~Q(order_line_items__stripe_invoice_line_item_id="BYPASS"),
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
                filter=~Q(order_line_items__rate=0)
                & ~Q(order_line_items__stripe_invoice_line_item_id="BYPASS"),
            ),
        )
        .aggregate(
            total_completed=Sum("customer_amount_completed"),
            total=Sum("customer_amount"),
        )
    )

    customer_amount_completed = customer_amounts["total_completed"] or Decimal("0.00")
    customer_amount = customer_amounts["total"] or Decimal("0.00")

    context["customer_amount_completed"] = customer_amount_completed
    context["customer_amount"] = customer_amount

    ##Net Revenue##
    # Supplier Amount Complete
    supplier_amounts = (
        Order.objects.filter(order_filter)
        .annotate(
            supplier_amount_complete=Sum(
                Case(
                    When(
                        Q(status="COMPLETE")
                        & ~Q(order_line_items__rate=0)
                        & ~Q(order_line_items__stripe_invoice_line_item_id="BYPASS"),
                        then=F("order_line_items__rate")
                        * F("order_line_items__quantity"),
                    ),
                    default=Value(0),
                    output_field=DecimalField(),
                )
            ),
            supplier_amount=Sum(
                F("order_line_items__rate") * F("order_line_items__quantity"),
                output_field=DecimalField(),
                filter=~Q(order_line_items__rate=0)
                & ~Q(order_line_items__stripe_invoice_line_item_id="BYPASS"),
            ),
        )
        .aggregate(
            total_complete=Sum("supplier_amount_complete"),
            total=Sum("supplier_amount"),
            total_scheduled=Sum(
                Case(
                    When(
                        Q(status="SCHEDULED")
                        & ~Q(order_line_items__rate=0)
                        & ~Q(order_line_items__stripe_invoice_line_item_id="BYPASS"),
                        then=F("order_line_items__rate")
                        * F("order_line_items__quantity"),
                    ),
                    default=Value(0),
                    output_field=DecimalField(),
                )
            ),
        )
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
    average_order_value = Order.objects.filter(order_filter).annotate(
        order_value=Sum(
            F("order_line_items__rate")
            * F("order_line_items__quantity")
            * (1 + F("order_line_items__platform_fee_percent") * 0.01),
            output_field=DecimalField(),
            filter=~Q(order_line_items__rate=0)
            & ~Q(order_line_items__stripe_invoice_line_item_id="BYPASS"),
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
    total_users = (
        Order.objects.filter(order_filter)
        .values("order_group__user_address__user_group__users__user_id")
        .distinct()
        .count()
    )
    context["total_users"] = total_users

    ##Total Companies##
    total_companies = (
        Order.objects.filter(order_filter)
        .values("order_group__user_address__user_group__name")
        .distinct()
        .count()
    )
    context["total_companies"] = total_companies

    ##Total Sellers##
    total_sellers = (
        Order.objects.filter(order_filter)
        .values("order_group__seller_product_seller_location__id")
        .distinct()
        .count()
    )
    context["total_sellers"] = total_sellers

    ##Total Listings##
    total_listings = (
        Order.objects.filter(order_filter)
        .values("order_group__seller_product_seller_location__id")
        .distinct()
        .count()
    )
    context["total_listings"] = total_listings

    ##Graphs##
    # GMV by Month Graph
    gmv_by_month = (
        Order.objects.filter(
            order_filter,
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
                        & ~Q(order_line_items__rate=0)
                        & ~Q(order_line_items__stripe_invoice_line_item_id="BYPASS"),
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
                        & ~Q(order_line_items__rate=0)
                        & ~Q(order_line_items__stripe_invoice_line_item_id="BYPASS"),
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
            order_filter,
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
                        & ~Q(order_line_items__rate=0)
                        & ~Q(order_line_items__stripe_invoice_line_item_id="BYPASS"),
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
                        & ~Q(order_line_items__rate=0)
                        & ~Q(order_line_items__stripe_invoice_line_item_id="BYPASS"),
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
                        & ~Q(order_line_items__rate=0)
                        & ~Q(order_line_items__stripe_invoice_line_item_id="BYPASS"),
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
                        & ~Q(order_line_items__rate=0)
                        & ~Q(order_line_items__stripe_invoice_line_item_id="BYPASS"),
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
            order_filter,
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
                        & ~Q(order_line_items__rate=0)
                        & ~Q(order_line_items__stripe_invoice_line_item_id="BYPASS"),
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
            order_filter,
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
                        & ~Q(order_line_items__rate=0)
                        & ~Q(order_line_items__stripe_invoice_line_item_id="BYPASS"),
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
                        & ~Q(order_line_items__rate=0)
                        & ~Q(order_line_items__stripe_invoice_line_item_id="BYPASS"),
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
            order_filter,
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
                        & ~Q(order_line_items__rate=0)
                        & ~Q(order_line_items__stripe_invoice_line_item_id="BYPASS"),
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
                        & ~Q(order_line_items__rate=0)
                        & ~Q(order_line_items__stripe_invoice_line_item_id="BYPASS"),
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

    orderRelations = (
        Order.objects.annotate(
            main_product_name=F(
                "order_group__seller_product_seller_location__seller_product__product__main_product__name"
            ),
            seller_location_name=F(
                "order_group__seller_product_seller_location__seller_location__name"
            ),
            payee_name=F(
                "order_group__seller_product_seller_location__seller_location__payee_name"
            ),
            project_location=F(
                "order_group__seller_product_seller_location__seller_location__payee_name"
            ),
            user_address_name=F("order_group__user_address__name"),
            end_date_anno=TruncMonth("end_date"),
            seller_amount=Sum(
                F("order_line_items__rate") * F("order_line_items__quantity"),
                output_field=DecimalField(),
            ),
            invoice_amount=Coalesce(
                Subquery(
                    Order.objects.filter(id=OuterRef("id"))
                    .annotate(
                        total_invoice_amount=Sum(
                            "seller_invoice_payable_line_items__amount"
                        )
                    )
                    .values("total_invoice_amount")[:1],
                ),
                Value(Decimal("0.00")),
                output_field=DecimalField(),
            ),
            variance=ExpressionWrapper(
                Abs(F("invoice_amount") - F("seller_amount")),
                output_field=DecimalField(),
            ),
            payout_amount=Coalesce(
                Subquery(
                    Payout.objects.filter(order_id=OuterRef("id"))
                    .values("order_id")
                    .annotate(total_payout_amount=Sum("amount"))
                    .values("total_payout_amount")[:1],
                ),
                Value(Decimal("0.00")),
                output_field=DecimalField(),
            ),
            reconcil_status=Case(
                When(seller_amount=F("invoice_amount"), then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            ),
            order_status=Case(
                When(payout_amount__isnull=True, then=Value("False")),
                When(
                    Q(invoice_amount__isnull=True)
                    & Q(payout_amount=F("seller_amount")),
                    then=Value("True"),
                ),
                When(payout_amount__gte=F("invoice_amount"), then=Value("True")),
                default=Value("False"),
                output_field=CharField(),
            ),
            payment_status=Case(
                When(order_status="True", then=Value("Paid")),
                default=Value("Unpaid"),
                output_field=CharField(),
            ),
            reconciliation_status=Case(
                When(reconcil_status=True, then=Value("Reconciled")),
                default=Value("Not Reconciled"),
                output_field=CharField(),
            ),
            combined_status=Func(
                F("payment_status"),
                Value(", "),
                F("reconciliation_status"),
                function="CONCAT",
                output_field=CharField(),
            ),
        )
        .values(
            "id",
            "main_product_name",
            "seller_location_name",
            "payee_name",
            "user_address_name",
            "end_date_anno",
            "seller_amount",
            "invoice_amount",
            "variance",
            "payout_amount",
            "combined_status",
        )
        .order_by("end_date_anno")
    )

    context["orderRelations"] = orderRelations

    # Define the order of statuses
    status_order = [
        "Paid, Reconciled",
        "Paid, Not Reconciled",
        "Unpaid, Reconciled",
        "Unpaid, Not Reconciled"
    ]

    # Group invoice_amount by month and combined_status
    monthly_invoice_amounts = defaultdict(lambda: defaultdict(float))
    for order in orderRelations:
        month = order["end_date_anno"].strftime("%Y-%m")
        status = order["combined_status"]
        monthly_invoice_amounts[month][status] += float(order["invoice_amount"] or 0.0)

    # Prepare data for chart.js
    chart_labels = sorted(monthly_invoice_amounts.keys())
    chart_data = {"labels": chart_labels, "datasets": []}
    status_colors = {
        "Paid, Reconciled": "rgba(25, 255, 25, 0.2)",
        "Paid, Not Reconciled": "rgba(144, 238, 144, 0.2)",
        "Unpaid, Reconciled": "rgba(255, 206, 86, 0.2)",
        "Unpaid, Not Reconciled": "rgba(255, 99, 132, 0.2)",
    }

    for status, color in status_colors.items():
        dataset = {
            "label": status,
            "data": [monthly_invoice_amounts[month].get(status, 0) for month in chart_labels],
            "backgroundColor": color,
            "borderColor": color.replace("0.2", "1"),
            "borderWidth": 1,
        }
        chart_data["datasets"].append(dataset)

    context["chart_data"] = json.dumps(chart_data)

    return render(request, "dashboards/payout_reconciliation.html", context)


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
        sellerlocation_name=F(
            "order_group__seller_product_seller_location__seller_location__name"
        ),
        mainproduct_name=F(
            "order_group__seller_product_seller_location__seller_product__product__main_product__name"
        ),
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


def auto_renewal_list_dashboard(request):
    context = {}
    # MAx end date subquery
    max_end_date_subquery = (
        Order.objects.filter(order_group=OuterRef("order_group"))
        .values("order_group")
        .annotate(max_end_date=Max("end_date"))
        .values("max_end_date")
    )
    today = now().date()
    orders = Order.objects.annotate(
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
    ).values(
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

    context["orders"] = orders
    return render(request, "dashboards/auto_renewal_list_dashboard.html", context)

def customer_first_order(request):
    context = {}
    user_groups = UserGroup.objects.annotate(
        user_id=F("user_addresses__order_groups__orders__order_group__user__id"),
        user_group_name=F("name"),
        user_first_name=F("user_addresses__order_groups__orders__order_group__user__first_name"),
        user_last_name=F("user_addresses__order_groups__orders__order_group__user__last_name"),
        user_email=F("user_addresses__order_groups__orders__order_group__user__email"),
        first_transaction_date=Subquery(
            Order.objects.filter(
                order_group__user=OuterRef("user_addresses__order_groups__orders__order_group__user")
            )
            .order_by()
            .values("order_group__user")
            .annotate(min_end_date=Min("end_date"))
            .values("min_end_date")[:1],
            output_field=DateField()
        ),
        has_order_review=Case(
            When(
                Exists(
                    OrderReview.objects.filter(
                        order_id=OuterRef("user_addresses__order_groups__orders__id")
                    )
                ),
                then=Value("Yes"),
            ),
            default=Value("No"),
            output_field=CharField(),
        )
    ).filter(
        first_transaction_date__year=2025,
    ).distinct()
    
    context["user_groups"] = user_groups
    return render(request, "dashboards/customer_first_order.html", context)


@login_required(login_url="/admin/login/")
def command_center(request):
    return render(
        request,
        "dashboards/index.html",
    )
