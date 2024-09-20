import logging

from django.contrib.auth.decorators import login_required

logger = logging.getLogger(__name__)
from django.shortcuts import render
from django.db.models import F, Sum, Avg, ExpressionWrapper, DecimalField
from django.http import JsonResponse
from datetime import datetime, timedelta


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


def index(request):
    # Hashmap
    context = {}

    # Translated Measures
    customerAmountCompleted = (
        Order.objects.filter(status="COMPLETE")
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
    customerAmountScheduled = (
        Order.objects.filter(status__in=["PENDING", "SCHEDULED"])
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
    context[customerAmountScheduled] = customerAmountScheduled

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
    supplierAmountCompleted = (
        Order.objects.filter(status="COMPLETE")
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
    context["supplierAmountCompleted"] = supplierAmountCompleted

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
            float(entry["suppAmount"]) if isinstance(entry["suppAmount"], Decimal)
            else float(0) if entry[suppAmount] is None
            else entry["suppAmount"]
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
    customerAmountCompleted_dict = [
        float(entry["gmv"]) if isinstance(entry["gmv"], Decimal) else entry["gmv"]
        for entry in customerAmountCompleted
    ]
    supplierAmountCompleted_dict = [
        (
            float(entry["suppAmountCompleted"])
            if isinstance(entry["suppAmountCompleted"], Decimal)
            else entry["suppAmountCompleted"]
        )
        for entry in supplierAmountCompleted
    ]

    netRevenueCompletedByMonth = {}
    supp_map = {
        entry["month"]: entry["suppAmountCompleted"]
        for entry in supplierAmountCompleted
    }
    for customer_entry in customerAmountCompleted:
        month = customer_entry["month"]
        gmv = customer_entry["gmv"]

        if month in supp_map:
            suppAmountCompleted = supp_map[month]
            difference = gmv - suppAmountCompleted
            netRevenueCompletedByMonth[month] = difference

    customerAmountCompleted_dictSum = sum(customerAmountCompleted_dict)
    supplierAmountCompleted_dictSum = sum(supplierAmountCompleted_dict)
    netRevenueCompletedSum = (
        customerAmountCompleted_dictSum - supplierAmountCompleted_dictSum
    )
    context["netRevenueCompleted"] = netRevenueCompletedSum

    # Net Revenue by day
    customerAmountByDay_dict = [
        (
            float(entry["customerAmntByDay"])
            if isinstance(entry["customerAmntByDay"], Decimal)
            else entry["customerAmntByDay"]
        )
        for entry in customerAmountByDay
    ]
    supplierAmountByDay_dict = [
        (
            float(entry["suppAmount"])
            if isinstance(entry["suppAmount"], Decimal)
            else entry["suppAmount"]
        )
        for entry in supplierAmountByDay
    ]
    netRevenueByDay = {}
    supp_map = {entry["day"]: entry["suppAmount"] for entry in supplierAmountByDay}
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
    data = [
        float(entry["gmv"]) if isinstance(entry["gmv"], Decimal) else entry["gmv"]
        for entry in customerAmountCompleted
    ]
    scheduleddata = [
        (
            float(entry["gmvScheduled"])
            if isinstance(entry["gmvScheduled"], Decimal)
            else entry["gmvScheduled"]
        )
        for entry in customerAmountScheduled
    ]
    context["chart_labels"] = labels
    context["chart_data"] = data
    context["chart_scheduled"] = scheduleddata

    # GMV
    GMV_Static = sum(data)
    context["GMV_Static"] = GMV_Static

    # Net Revenue by Month Bar Chart
    labels2 = [key.strftime("%Y-%m") for key in netRevenueCompletedByMonth.keys()]
    data2 = [float(value) for value in netRevenueCompletedByMonth.values()]

    context["netRevGraph_labels"] = labels2
    context["netRevGraph_data"] = data2

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


@login_required(login_url="/admin/login/")
def command_center(request):
    return render(
        request,
        "dashboards/index.html",
    )
