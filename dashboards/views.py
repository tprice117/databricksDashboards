import logging

from django.contrib.auth.decorators import login_required

logger = logging.getLogger(__name__)
from django.shortcuts import render
from django.db.models import F, Sum, Avg, ExpressionWrapper, DecimalField, FloatField, Case, When, Value, CharField, Count, Func
from django.http import JsonResponse

from django.db.models.functions import ExtractYear
from api.models.seller.seller import *
from api.models.order.order import *
from api.models.order.order_group import *
from api.models.order.order_line_item import *
from api.models.user.user_group import *
from django.db.models.functions import Coalesce
from django.db.models.functions import TruncMonth, TruncDay
from decimal import Decimal
from django.db.models import Q
from django.utils import timezone
from collections import defaultdict

import requests

from datetime import datetime, timedelta



def index(request):
    # Hashmap
    context = {}

    # Translated Measures
    # Define the date range for filtering
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
        # Define the date range for filtering

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

    return render(request, "dashboards/index.html", context)


def pbiimport(request):
    context = {}
    report_url = "https://app.powerbi.com/reportEmbed?reportId=cbf09a4c-afd3-4b30-b682-8e9c331bdbf5&autoAuth=true&ctid=5a7d42d9-b3cf-4720-b6c0-8836594679d6"
    context["report_url"] = report_url
    return render(request, "dashboards/pbiimport.html", context)


def poatest(request):
    return render(request, "dashboards/poatest.html")


def payout_reconciliation(request):
    context = {}

    orderRelations = (
        Order.objects.annotate(
            main_product_name=F("order_group__seller_product_seller_location__seller_product__product__main_product__name"),
            seller_location_names=F("order_group__seller_product_seller_location__seller_location__name"),
            user_address=F("order_group__user_address__name"),
            end_date_annotate=F("end_date"),
            supplier_amount=ExpressionWrapper(F("order_line_items__rate") * F("order_line_items__quantity"), output_field=FloatField()),
            seller_invoice_amount=Sum('seller_invoice_payable_line_items__amount'),
            payout_amount=F("payouts__amount"),
            # -- TODO -- reconcil status
            order_url_annotate=Func(
                Value("https://monkfish-app-donig.ondigitalocean.app/admin/api/order/"),
                F("id"),
                Value("/change/"),
                function="CONCAT",
                output_field=CharField()
            )


        ).values(
            "id",
            "main_product_name",
            "seller_location_names",
            "user_address",
            "end_date_annotate",
            "supplier_amount",
            "seller_invoice_amount",
            "payout_amount",
            # -- TODO -- reconcil status
            "order_url_annotate"

        )
    )
    context["orderRelations"] = orderRelations
    return render(request, "dashboards/payout_reconciliation.html", context)



@login_required(login_url="/admin/login/")
def command_center(request):
    return render(
        request,
        "dashboards/index.html",
    )
