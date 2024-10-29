import logging

from django.contrib.auth.decorators import login_required
from collections import defaultdict


logger = logging.getLogger(__name__)
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
)
from django.http import JsonResponse
from django.db.models import Subquery, OuterRef

from django.db.models.functions import ExtractYear
from api.models import *
from api.models.seller.seller import *
from api.models.order.order import *
from api.models.order.order_group import *
from api.models.order.order_line_item import *
from api.models.user.user_group import *
from django.db.models.functions import Coalesce, Round
from django.db.models.functions import TruncMonth, TruncDay
from decimal import Decimal
from django.utils import timezone
from collections import defaultdict
from django.db.models.functions import Abs
from django.core.paginator import Paginator

import requests
import json
from datetime import datetime, timedelta


def index(request):
    return render(request, "dashboards/index.html")


def sales_dashboard(request):
    # Hashmap
    context = {}

    # Translated Measures
    # Define date range for filtering
    start_date = datetime(datetime.now().year - 1, 1, 1)
    end_date = datetime(datetime.now().year, 12, 31)

    customerAmountCompleted = (
        Order.objects.filter(status="COMPLETE", end_date__range=(start_date, end_date))
        .annotate(month=TruncMonth("end_date"))  # Groupby month
        .values("month")
        .annotate(
            gmv=Sum(
                ExpressionWrapper(
                    F("order_line_items__rate")
                    * F("order_line_items__quantity")
                    * (1 + F("order_line_items__platform_fee_percent") * 0.01),
                    output_field=DecimalField(),
                )
            )
        )
        .order_by("month")
    )
    context["customerAmountCompleted"] = customerAmountCompleted

    # customerAmountScheduled
    def calculate_pending_scheduled_gmv():
        return (
            Order.objects.filter(
                status__in=["PENDING", "SCHEDULED"],
                end_date__range=(start_date, end_date),
            )
            .annotate(month=TruncMonth("end_date"))
            .values("month")
            .annotate(
                gmvScheduled=Sum(
                    ExpressionWrapper(
                        F("order_line_items__rate")
                        * F("order_line_items__quantity")
                        * (1 + F("order_line_items__platform_fee_percent") * 0.01),
                        output_field=DecimalField(),
                    )
                )
            )
            .order_by("month")
        )

    customerAmountScheduled = calculate_pending_scheduled_gmv()
    context["customerAmountScheduled"] = customerAmountScheduled

    # customerAmount
    customerAmount = (
        OrderLineItem.objects.annotate(month=TruncMonth("order__end_date"))
        .values("month")
        .annotate(
            customerAmnt=Sum(
                ExpressionWrapper(
                    F("rate") * F("quantity") * (1 + F("platform_fee_percent") * 0.01),
                    output_field=DecimalField(),
                )
            )
        )
        .filter(order__end_date__year=2024)
        .order_by("month")
    )
    customerAmount_dict = [
        (
            float(entry["customerAmnt"])
            if isinstance(entry["customerAmnt"], Decimal)
            else entry["customerAmnt"]
        )
        for entry in customerAmount
    ]
    customerAmount_dictSum = Decimal(sum(customerAmount_dict))
    context["customerAmount"] = customerAmount

    # customerAmountbyDay
    delta_month = timezone.now() - timedelta(days=30)

    customerAmountByDay = (
        OrderLineItem.objects.annotate(day=TruncDay("order__end_date"))
        .values("day")
        .annotate(
            customerAmntByDay=Sum(
                ExpressionWrapper(
                    F("rate") * F("quantity") * (1 + F("platform_fee_percent") * 0.01),
                    output_field=DecimalField(),
                )
            )
        )
        .filter(order__end_date__gte=delta_month)
        .order_by("day")
    )
    customerAmountByDay_dict = [
        (
            float(entry["customerAmntByDay"])
            if isinstance(entry["customerAmntByDay"], Decimal)
            else entry["customerAmntByDay"]
        )
        for entry in customerAmountByDay
    ]
    customerAmountByDay_dictSum = Decimal(sum(customerAmountByDay_dict))
    context["customerAmountByDay"] = customerAmountByDay

    # supplierAmountCompleted

    def calculate_supplier_amount_completed(start_date, end_date):
        return (
            Order.objects.filter(
                status="COMPLETE", end_date__range=(start_date, end_date)
            )
            .annotate(month=TruncMonth("end_date"))  # Groupby month
            .values("month")
            .annotate(
                suppAmountCompleted=Sum(
                    ExpressionWrapper(
                        F("order_line_items__rate") * F("order_line_items__quantity"),
                        output_field=DecimalField(),
                    )
                )
            )
            .order_by("month")
        )

    supplierAmountCompleted = calculate_supplier_amount_completed(start_date, end_date)
    context["supplierAmountCompleted"] = supplierAmountCompleted

    # supplierAmountScheduled
    def calculate_pending_scheduled_supplier_amount():
        return (
            Order.objects.filter(
                status__in=["PENDING", "SCHEDULED"],
                end_date__range=(start_date, end_date),
            )
            .annotate(month=TruncMonth("end_date"))
            .values("month")
            .annotate(
                suppAmountScheduled=Sum(
                    ExpressionWrapper(
                        F("order_line_items__rate") * F("order_line_items__quantity"),
                        output_field=DecimalField(),
                    )
                )
            )
            .order_by("month")
        )

    supplierAmountScheduled = calculate_pending_scheduled_supplier_amount()
    context["supplierAmountScheduled"] = supplierAmountScheduled

    # supplierAmount
    supplierAmount = (
        Order.objects.annotate(month=TruncMonth("end_date"))  # Groupby month
        .values("month")
        .annotate(
            suppAmount=Sum(
                ExpressionWrapper(
                    F("order_line_items__rate") * F("order_line_items__quantity"),
                    output_field=DecimalField(),
                )
            )
        )
        .order_by("month")
        .filter(end_date__year=2024)
    )
    context["supplierAmount"] = supplierAmount
    supplierAmount_dict = [
        (
            float(entry["suppAmount"])
            if isinstance(entry["suppAmount"], Decimal)
            else entry["suppAmount"]
        )
        for entry in supplierAmount
    ]

    # SupplierAmountbyDay
    supplierAmountByDay = (
        Order.objects.annotate(day=TruncDay("end_date"))  # Groupby day
        .values("day")
        .annotate(
            suppAmount=Sum(
                ExpressionWrapper(
                    F("order_line_items__rate") * F("order_line_items__quantity"),
                    output_field=DecimalField(),
                )
            )
        )
        .order_by("day")
        .filter(end_date__year=2024)
    )
    context["supplierAmountByDay"] = supplierAmountByDay
    supplierAmountByDay_dict = [
        (
            float(entry["suppAmount"])
            if isinstance(entry["suppAmount"], Decimal)
            else float(0) if entry[suppAmount] is None else entry["suppAmount"]
        )
        for entry in supplierAmount
    ]
    # supplierAmountSum
    supplierAmountSum = Order.objects.annotate(
        calculated_value=Sum(
            F("order_line_items__rate") * F("order_line_items__quantity"),
            output_field=DecimalField(),
        )
    ).aggregate(total=Sum("calculated_value"))["total"]
    context["supplierAmountSum"] = supplierAmountSum

    # Net Revenue Completed
    def calculate_net_revenue_completed(
        customer_amount_completed, supplier_amount_completed
    ):
        net_revenue_completed = []
        for customer_entry in customer_amount_completed:
            month = customer_entry["month"]
            customer_gmv = customer_entry["gmv"]

            # Find the corresponding supplier amount for the same month
            supplier_entry = next(
                (
                    entry
                    for entry in supplier_amount_completed
                    if entry["month"] == month
                ),
                None,
            )
            if supplier_entry:
                supplier_amount = supplier_entry["suppAmountCompleted"]
                net_revenue = customer_gmv - supplier_amount
                net_revenue_completed.append(
                    {"month": month, "netRevenue": net_revenue}
                )

        return net_revenue_completed

    net_revenue_completed_by_month = calculate_net_revenue_completed(
        customerAmountCompleted, supplierAmountCompleted
    )
    net_revenue_completed_sum = sum(
        entry["netRevenue"] for entry in net_revenue_completed_by_month
    )
    context["netRevenueCompletedSum"] = net_revenue_completed_sum
    context["netRevenueCompletedByMonth"] = net_revenue_completed_by_month

    # Net Revenue Scheduled
    def calculate_net_revenue_scheduled(
        customer_amount_scheduled, supplier_amount_scheduled
    ):
        net_revenue_scheduled = []
        for customer_entry in customer_amount_scheduled:
            month = customer_entry["month"]
            customer_gmv_scheduled = customer_entry["gmvScheduled"]

        # Find the corresponding supplier amount for the same month
        supplier_entry = next(
            (entry for entry in supplier_amount_scheduled if entry["month"] == month),
            None,
        )
        if supplier_entry:
            supplier_amount = supplier_entry["suppAmountScheduled"]
            net_revenue = customer_gmv_scheduled - supplier_amount
            net_revenue_scheduled.append(
                {"month": month, "netRevenueScheduled": net_revenue}
            )

        return net_revenue_scheduled

    netRevenueScheduledByMonth = calculate_net_revenue_scheduled(
        customerAmountScheduled, supplierAmountScheduled
    )
    context["netRevenueScheduled"] = netRevenueScheduledByMonth

    # Net Revenue by day
    netRevenueByDay = {}
    supp_map = {entry["day"]: entry["suppAmount"] for entry in supplierAmountByDay}
    # Filter down to the past month of data
    past_month = timezone.now() - timedelta(days=30)
    customerAmountByDay = customerAmountByDay.filter(day__gte=past_month)
    supplierAmountByDay = supplierAmountByDay.filter(day__gte=past_month)

    for customer_entry in customerAmountByDay:
        day = customer_entry["day"]
        customerAmnt = customer_entry["customerAmntByDay"]

        if day in supp_map:
            suppAmount = supp_map[day]
            difference = customerAmnt - suppAmount
            netRevenueByDay[day] = difference

    netRevenueByMonth_labels = []
    netRevenueByMonth_data = []
    customerAmount_dictSum = sum(customerAmountByDay_dict)
    # supplierAmount_dictSum = sum(supplierAmountByDay_dict)
    supplierAmount_dictSum = 0

    netRevenueSum = customerAmount_dictSum - supplierAmount_dictSum
    context["netRevenueByMonth"] = netRevenueByDay
    # Users Count
    userCount = OrderGroup.objects.values("user").distinct().count()
    context["userCount"] = userCount

    # Companies Count
    userGroupCount = UserGroup.objects.values("name").distinct().count()
    context["userGroupCount"] = userGroupCount

    # Suppliers Count
    sellerCount = (
        OrderGroup.objects.values("seller_product_seller_location_id")
        .distinct()
        .count()
    )
    context["sellerCount"] = sellerCount

    # SPSL Count
    spslCount = OrderGroup.objects.values("seller_product_seller_location_id").count()
    context["spslCount"] = spslCount

    # Average Order Value
    orderSum = Order.objects.annotate(
        caluclated_val=Sum(
            F("order_line_items__rate")
            * F("order_line_items__quantity")
            * (1 + F("order_line_items__platform_fee_percent") * 0.01),
            output_field=DecimalField(),
        )
    )
    avgOrderValue = orderSum.aggregate(average=Avg("caluclated_val"))["average"]
    avgOrderValue = round(avgOrderValue, 2)
    context["avgOrderValue"] = avgOrderValue

    # Take Rate By Month
    takeRateByMonth = (
        OrderLineItem.objects.annotate(month=TruncMonth("order__end_date"))
        .values("month")
        .annotate(
            customerAmnt=Sum(
                ExpressionWrapper(
                    F("rate") * F("quantity") * (1 + F("platform_fee_percent") * 0.01),
                    output_field=DecimalField(),
                )
            ),
            supplierAmnt=Sum(
                F("rate") * F("quantity")
            ),  # Assuming supplierAmountSum is calculated like this
        )
        .order_by("month")
    )
    takeRateData = []
    for entry in takeRateByMonth:
        customerAmount = entry["customerAmnt"]
        supplierAmountSum = entry["supplierAmnt"]
        takeRate = round(
            ((customerAmount - supplierAmountSum) / customerAmount) * 100, 1
        )

        takeRateData.append(
            {"month": entry["month"].strftime("%Y-%m"), "takeRate": takeRate}
        )
    context["takeRateData"] = takeRateData

    # GMVByMonthGraph
    labels = [entry["month"].strftime("%Y-%m") for entry in customerAmountCompleted]
    gmv_data = {
        entry["month"].strftime("%Y-%m"): (
            float(entry["gmv"]) if isinstance(entry["gmv"], Decimal) else entry["gmv"]
        )
        for entry in customerAmountCompleted
    }

    scheduled_data = {
        entry["month"].strftime("%Y-%m"): (
            float(entry["gmvScheduled"])
            if isinstance(entry["gmvScheduled"], Decimal)
            else entry["gmvScheduled"]
        )
        for entry in customerAmountScheduled
    }
    all_months = sorted(set(gmv_data.keys()).union(scheduled_data.keys()))

    labels = all_months
    data = [gmv_data.get(month, 0) for month in all_months]
    scheduleddata = [scheduled_data.get(month, 0) for month in all_months]

    context["chart_labels"] = labels
    context["chart_data"] = data
    context["chart_scheduled"] = scheduleddata

    # GMV
    GMV_Static = sum(data)
    context["GMV_Static"] = GMV_Static

    # Take Rate Static
    takeRate_Static = (customerAmnt - supplierAmountSum) / customerAmnt * 100
    context["takeRate_Static"] = takeRate_Static

    # Net Revenue by Month Bar Chart
    netRevenueCompleted_data = {
        entry["month"].strftime("%Y-%m"): float(entry["netRevenue"])
        for entry in net_revenue_completed_by_month
    }
    netRevenueScheduled_data = {
        entry["month"].strftime("%Y-%m"): float(entry["netRevenueScheduled"])
        for entry in netRevenueScheduledByMonth
    }

    all_months_net_revenue = sorted(
        set(netRevenueCompleted_data.keys()).union(netRevenueScheduled_data.keys())
    )

    netRevenueCompletedGraph_data = [
        netRevenueCompleted_data.get(month, 0) for month in all_months_net_revenue
    ]
    netRevenueScheduledGraph_data = [
        netRevenueScheduled_data.get(month, 0) for month in all_months_net_revenue
    ]

    context["netRevGraph_labels"] = all_months_net_revenue
    context["netRevenueCompletedGraph_data"] = netRevenueCompletedGraph_data
    context["netRevenueScheduledGraph_data"] = netRevenueScheduledGraph_data
    # Daily GMV Rate LineChart
    labels3 = [entry["day"].strftime("%Y-%m-%d") for entry in customerAmountByDay]
    data3 = [
        (
            float(entry["customerAmntByDay"])
            if isinstance(entry["customerAmntByDay"], Decimal)
            else entry["customerAmntByDay"]
        )
        for entry in customerAmountByDay
    ]

    context["GMVGraph_labels"] = labels3
    context["GMVGraph_data"] = data3

    # TakeRate LineChart

    labels4 = [entry["month"] for entry in takeRateData]
    data4 = [
        (
            float(entry["takeRate"])
            if isinstance(entry["takeRate"], Decimal)
            else entry["takeRate"]
        )
        for entry in takeRateData
    ]
    context["takeRateData_labels"] = labels4
    context["takeRateData_data"] = data4

    # Daily Net Revenue Rate line Chart
    labels5 = [key.strftime("%Y-%m-%d") for key in netRevenueByDay.keys()]
    data5 = [float(value) for value in netRevenueByDay.values()]
    context["NetRev_labels"] = labels5
    context["NetRev_data"] = data5

    return render(request, "dashboards/sales_dashboard.html", context)


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
            id=OuterRef('order_group__seller_product_seller_location__seller_location__id')
        ).values('name')[:1]
    )
    
    user_address_subquery = Subquery(
        UserAddress.objects.filter(
            id=OuterRef('order_group__user_address__id')
        ).values('name')[:1]
    )
    
    orderRelations = Order.objects.annotate(
        main_product_name=F("order_group__seller_product_seller_location__seller_product__product__main_product__name"),
        seller_location_names=seller_location_names_subquery,
        user_address=user_address_subquery,
        end_date_annotate=F("end_date"),
        supplier_amount=ExpressionWrapper(
            Round(F("order_line_items__rate") * F("order_line_items__quantity"), 2),
            output_field=DecimalField(decimal_places=2),
        ),
        seller_invoice_amount=Coalesce(F("seller_invoice_payable_line_items__amount"), Value(0), output_field=DecimalField(decimal_places=2)),
        payout_amount=Coalesce(F("payouts__amount"), Value(0), output_field=DecimalField(decimal_places=2)),
        abs_difference=ExpressionWrapper(
            Abs(F('seller_invoice_amount') - F('supplier_amount')),
            output_field=FloatField()
        ),
        reconcil_status=Case(
            When(
                abs_difference__lt=0.01,
                then=Value('Reconciled')
            ),
            default=Value('Not Reconciled'),
            output_field=CharField()
        ),
        order_status=Case(
            When(
                payout_amount__isnull=True,
                then=Value('Unpaid')
            ),
            When(
                seller_invoice_amount__isnull=True,
                payout_amount=F('supplier_amount'),
                then=Value('Paid')
            ),
            When(
                payout_amount__gte=F('seller_invoice_amount'),
                then=Value('Paid')
            ),
            default=Value('Unpaid'),
            output_field=CharField()
        ),
        order_status_comb=Func(
            F('order_status'),
            Value(', '),
            F('reconcil_status'),
            function='CONCAT',
            output_field=CharField()
        ),
        order_url_annotate=Func(
            Value(settings.DASHBOARD_BASE_URL + "/"),
            Value("admin/api/order/"),
            F("id"),
            Value("/change/"),
            function="CONCAT",
            output_field=CharField(),
        ),
    ).distinct('id').values(
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

    unique_order_status_comb = set(order["order_status_comb"] for order in orderRelations)
    total_seller_invoice_amount = sum(
        float(order["seller_invoice_amount"] or 0) for order in orderRelations
    )
    context["total_seller_invoice_amount"] = total_seller_invoice_amount

    # Group by month and sum seller_invoice_amount for each order_status_comb
    monthly_data = defaultdict(lambda: defaultdict(float))
    for order in orderRelations:
        order_date = order["end_date_annotate"]
        month = order_date.strftime("%Y-%m")  # Format as YYYY-MM
        seller_invoice_amount = order["seller_invoice_amount"] or 0  # Replace None with 0
        order_status_comb = order["order_status_comb"]
        monthly_data[month][order_status_comb] += float(seller_invoice_amount)

    sorted_monthly_data = {month: dict(status_data) for month, status_data in sorted(monthly_data.items())}

    # Prep for chart.js
    chart_data = {
        "labels": list(sorted_monthly_data.keys()),
        "datasets": []
    }

    # Define colors for each status
    status_colors = {
        "Paid, Reconciled": "rgba(75, 192, 192, 0.2)",
        "Paid, Not Reconciled": "rgba(255, 206, 86, 0.2)",
        "Unpaid, Reconciled": "rgba(153, 102, 255, 0.2)",
        "Unpaid, Not Reconciled": "rgba(255, 99, 132, 0.2)"
    }

    for status, color in status_colors.items():
        dataset = {
            "label": status,
            "data": [monthly_data[month].get(status, 0) for month in chart_data["labels"]],
            "backgroundColor": color,
            "borderColor": color.replace("0.2", "1"),
            "borderWidth": 1
        }
        chart_data["datasets"].append(dataset)

    # Convert to json
    chart_data_json = json.dumps(chart_data)

    context["chart_data"] = chart_data_json
    context["orderRelations"] = orderRelations
    paginator = Paginator(orderRelations, 30)  # Show 30 orders per page

    page_number = request.GET.get('page')
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
