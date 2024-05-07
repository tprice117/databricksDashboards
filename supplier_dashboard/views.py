from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from typing import List
import json
from django.contrib import messages
from urllib.parse import parse_qs
import datetime
from itertools import chain
from django.http import HttpResponse, HttpResponseRedirect
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
import logging

from api.models import (
    User,
    Order,
    Seller,
    Payout,
    SellerInvoicePayable,
    SellerLocation,
    SellerInvoicePayableLineItem,
    SellerLocationMailingAddress,
)
from api.utils.utils import decrypt_string
from notifications.utils import internal_email
from communications.intercom.utils.utils import get_json_safe_value
from .forms import (
    UserForm,
    SellerForm,
    SellerCommunicationForm,
    SellerAboutUsForm,
    SellerLocationComplianceForm,
    SellerPayoutForm,
)

logger = logging.getLogger(__name__)


class InvalidFormError(Exception):
    """Exception raised for validation errors in the form."""

    def __init__(self, form, msg):
        self.form = form
        self.msg = msg

    def __str__(self):
        return self.msg


def to_dict(instance):
    opts = instance._meta
    data = {}
    for f in chain(opts.concrete_fields, opts.private_fields):
        data[f.name] = get_json_safe_value(f.value_from_object(instance))
    for f in opts.many_to_many:
        data[f.name] = [
            get_json_safe_value(i.id) for i in f.value_from_object(instance)
        ]
    return data


def get_dashboard_chart_data(data_by_month: List[int]):
    # Create a list of labels along with earnings data of months going back from the current month to 8 months ago.
    data = []
    all_months = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]
    current_month = datetime.date.today().month
    months = []
    for i in range(8, 1, -1):
        months.append(all_months[(current_month - i - 1) % 12])
        data.append(data_by_month[(current_month - i - 1) % 12])

    dashboard_chart = {
        "type": "line",
        "data": {
            "labels": months,
            "datasets": [
                {
                    "label": "Earnings",
                    "fill": True,
                    "data": data,
                    "backgroundColor": "rgba(78, 115, 223, 0.05)",
                    "borderColor": "rgba(78, 115, 223, 1)",
                }
            ],
        },
        "options": {
            "maintainAspectRatio": False,
            "legend": {"display": False, "labels": {"fontStyle": "normal"}},
            "title": {"fontStyle": "normal"},
            "scales": {
                "xAxes": [
                    {
                        "gridLines": {
                            "color": "rgb(234, 236, 244)",
                            "zeroLineColor": "rgb(234, 236, 244)",
                            "drawBorder": False,
                            "drawTicks": False,
                            "borderDash": ["2"],
                            "zeroLineBorderDash": ["2"],
                            "drawOnChartArea": False,
                        },
                        "ticks": {
                            "fontColor": "#858796",
                            "fontStyle": "normal",
                            "padding": 20,
                        },
                    }
                ],
                "yAxes": [
                    {
                        "gridLines": {
                            "color": "rgb(234, 236, 244)",
                            "zeroLineColor": "rgb(234, 236, 244)",
                            "drawBorder": False,
                            "drawTicks": False,
                            "borderDash": ["2"],
                            "zeroLineBorderDash": ["2"],
                        },
                        "ticks": {
                            "fontColor": "#858796",
                            "fontStyle": "normal",
                            "padding": 20,
                        },
                    }
                ],
            },
        },
    }
    return dashboard_chart


########################
# Page views
########################
# Add redirect to auth0 login if not logged in.
@login_required(login_url="/supplier/login/")
def supplier_login(request):
    pass


@login_required(login_url="/admin/login/")
def supplier_select(request):
    if request.method == "POST":
        seller_id = request.POST.get("seller_id")
    elif request.method == "GET":
        seller_id = request.GET.get("seller_id")
    else:
        return HttpResponse("Not Implemented", status=406)
    try:
        seller = Seller.objects.get(id=seller_id)
        request.session["seller"] = to_dict(seller)
        return HttpResponseRedirect("/supplier/")
    except Exception as e:
        return HttpResponse("Not Found", status=404)


@login_required(login_url="/admin/login/")
def index(request):
    context = {}
    context["user"] = request.user
    if not request.session.get("seller"):
        request.session["seller"] = to_dict(request.user.user_group.seller)
    context["seller"] = request.session["seller"]
    orders = Order.objects.filter(
        order_group__seller_product_seller_location__seller_product__seller_id=context[
            "seller"
        ]["id"]
    )
    # .filter(status=Order.PENDING)
    context["earnings"] = 0
    earnings_by_category = {}
    pending_count = 0
    scheduled_count = 0
    complete_count = 0
    cancelled_count = 0
    earnings_by_month = [0] * 12
    for order in orders:
        context["earnings"] += float(order.seller_price())
        earnings_by_month[order.end_date.month - 1] += float(order.seller_price())

        category = (
            order.order_group.seller_product_seller_location.seller_product.product.main_product.main_product_category.name
        )
        if category not in earnings_by_category:
            earnings_by_category[category] = {"amount": 0, "percent": 0}
        earnings_by_category[category]["amount"] += float(order.seller_price())

        if order.status == Order.PENDING:
            pending_count += 1
        elif order.status == Order.SCHEDULED:
            scheduled_count += 1
        elif order.status == Order.COMPLETE:
            complete_count += 1
        elif order.status == Order.CANCELLED:
            cancelled_count += 1

    # # Just test data here
    # earnings_by_category["Business Dumpster"] = {"amount": 2000, "percent": 0}
    # earnings_by_category["Junk Removal"] = {"amount": 5000, "percent": 0}
    # earnings_by_category["Scissor Lift"] = {"amount": 100, "percent": 0}
    # earnings_by_category["Concrete & Masonary"] = {
    #     "amount": 50,
    #     "percent": 0,
    # }
    # earnings_by_category["Office Unit"] = {"amount": 25, "percent": 0}
    # earnings_by_category["Forklift"] = {"amount": 80, "percent": 0}
    # earnings_by_category["Boom Lifts"] = {"amount": 800, "percent": 0}
    # context["earnings"] += 200 + 500 + 100 + 50 + 25 + 80 + 800

    # Sort the dictionary by the 'amount' field in descending order
    sorted_categories = sorted(
        earnings_by_category.items(), key=lambda x: x[1]["amount"], reverse=True
    )

    # Calculate the 'percent' field for each category
    for category, data in sorted_categories:
        data["percent"] = int((data["amount"] / context["earnings"]) * 100)

    # Create a new category 'Other' for the categories that are not in the top 4
    other_amount = sum(data["amount"] for category, data in sorted_categories[4:])
    other_percent = int((other_amount / context["earnings"]) * 100)

    # Create the final dictionary
    final_categories = dict(sorted_categories[:4])
    final_categories["Other"] = {"amount": other_amount, "percent": other_percent}
    context["earnings_by_category"] = final_categories
    # print(final_categories)
    context["pending_count"] = pending_count
    seller_locations = SellerLocation.objects.filter(seller_id=context["seller"]["id"])
    # context["pending_count"] = orders.count()
    context["location_count"] = seller_locations.count()
    context["user_count"] = User.objects.filter(
        user_group__seller_id=context["seller"]["id"]
    ).count()

    context["chart_data"] = json.dumps(get_dashboard_chart_data(earnings_by_month))

    if request.headers.get("HX-Request"):
        context["page_title"] = "Dashboard"
        return render(request, "supplier_dashboard/snippets/dashboard.html", context)
    else:
        return render(request, "supplier_dashboard/index.html", context)


@login_required(login_url="/admin/login/")
def profile(request):
    context = {}
    context["user"] = request.user
    if not request.session.get("seller"):
        request.session["seller"] = to_dict(request.user.user_group.seller)
    context["seller"] = request.session["seller"]

    if request.method == "POST":
        form = UserForm(request.POST)
        context["form"] = form
        if form.is_valid():
            save_db = False
            if form.cleaned_data.get("first_name") != request.user.first_name:
                request.user.first_name = form.cleaned_data.get("first_name")
                save_db = True
            if form.cleaned_data.get("last_name") != request.user.last_name:
                request.user.last_name = form.cleaned_data.get("last_name")
                save_db = True
            if form.cleaned_data.get("phone") != request.user.phone:
                request.user.phone = form.cleaned_data.get("phone")
                save_db = True
            if form.cleaned_data.get("photo_url") != request.user.photo_url:
                request.user.photo_url = form.cleaned_data.get("photo_url")
                save_db = True
            if save_db:
                request.user.save()
                messages.success(request, "Successfully saved!")
            else:
                messages.info(request, "No changes detected.")
            # return HttpResponse("", status=200)
            # This is an HTMX request, so respond with html snippet
            if request.headers.get("HX-Request"):
                return render(request, "supplier_dashboard/profile.html", context)
            else:
                return render(request, "supplier_dashboard/profile.html", context)
        else:
            # This will let bootstrap know to highlight the fields with errors.
            for field in form.errors:
                form[field].field.widget.attrs["class"] += " is-invalid"
            # messages.error(request, "Error saving, please contact us if this continues.")
    else:
        form = UserForm(
            initial={
                "first_name": request.user.first_name,
                "last_name": request.user.last_name,
                "phone": request.user.phone,
                "photo_url": request.user.photo_url,
                "email": request.user.email,
            }
        )
        context["form"] = form
    return render(request, "supplier_dashboard/profile.html", context)


@login_required(login_url="/admin/login/")
def company(request):
    context = {}
    context["user"] = request.user
    if not request.session.get("seller"):
        request.session["seller"] = to_dict(request.user.user_group.seller)
    context["seller"] = request.session["seller"]
    if request.method == "POST":
        try:
            save_model = None
            if "company_submit" in request.POST:
                # Load other forms so template has complete data.
                seller_communication_form = SellerCommunicationForm(
                    initial={
                        "dispatch_email": request.user.user_group.seller.order_email,
                        "dispatch_phone": request.user.user_group.seller.order_phone,
                    }
                )
                context["seller_communication_form"] = seller_communication_form
                seller_about_us_form = SellerAboutUsForm(
                    initial={"about_us": request.user.user_group.seller.about_us}
                )
                context["seller_about_us_form"] = seller_about_us_form
                # Load the form that was submitted.
                form = SellerForm(request.POST)
                context["form"] = form
                if form.is_valid():
                    if (
                        form.cleaned_data.get("company_name")
                        != request.user.user_group.seller.name
                    ):
                        request.user.user_group.seller.name = form.cleaned_data.get(
                            "company_name"
                        )
                        save_model = request.user.user_group.seller
                    if (
                        form.cleaned_data.get("company_phone")
                        != request.user.user_group.seller.phone
                    ):
                        request.user.user_group.seller.phone = form.cleaned_data.get(
                            "company_phone"
                        )
                        save_model = request.user.user_group.seller
                    if (
                        form.cleaned_data.get("website")
                        != request.user.user_group.seller.website
                    ):
                        request.user.user_group.seller.website = form.cleaned_data.get(
                            "website"
                        )
                        save_model = request.user.user_group.seller
                    if (
                        form.cleaned_data.get("company_logo")
                        != request.user.user_group.seller.location_logo_url
                    ):
                        request.user.user_group.seller.location_logo_url = (
                            form.cleaned_data.get("company_logo")
                        )
                        save_model = request.user.user_group.seller
                else:
                    raise InvalidFormError(form, "Invalid SellerForm")
            elif "communication_submit" in request.POST:
                # Load other forms so template has complete data.
                form = SellerForm(
                    initial={
                        "company_name": request.user.user_group.seller.name,
                        "company_phone": request.user.user_group.seller.phone,
                        "website": request.user.user_group.seller.website,
                        "company_logo": request.user.user_group.seller.location_logo_url,
                    }
                )
                context["form"] = form
                seller_about_us_form = SellerAboutUsForm(
                    initial={"about_us": request.user.user_group.seller.about_us}
                )
                context["seller_about_us_form"] = seller_about_us_form
                # Load the form that was submitted.
                seller_communication_form = SellerCommunicationForm(request.POST)
                context["seller_communication_form"] = seller_communication_form
                if seller_communication_form.is_valid():
                    save_model = None
                    if (
                        seller_communication_form.cleaned_data.get("dispatch_email")
                        != request.user.user_group.seller.order_email
                    ):
                        request.user.user_group.seller.order_email = (
                            seller_communication_form.cleaned_data.get("dispatch_email")
                        )
                        save_model = request.user.user_group.seller
                    if (
                        seller_communication_form.cleaned_data.get("dispatch_phone")
                        != request.user.user_group.seller.order_phone
                    ):
                        request.user.user_group.seller.order_phone = (
                            seller_communication_form.cleaned_data.get("dispatch_phone")
                        )
                        save_model = request.user.user_group.seller
                else:
                    raise InvalidFormError(
                        seller_communication_form, "Invalid SellerCommunicationForm"
                    )
            elif "about_us_submit" in request.POST:
                # Load other forms so template has complete data.
                form = SellerForm(
                    initial={
                        "company_name": request.user.user_group.seller.name,
                        "company_phone": request.user.user_group.seller.phone,
                        "website": request.user.user_group.seller.website,
                        "company_logo": request.user.user_group.seller.location_logo_url,
                    }
                )
                context["form"] = form
                seller_communication_form = SellerCommunicationForm(
                    initial={
                        "dispatch_email": request.user.user_group.seller.order_email,
                        "dispatch_phone": request.user.user_group.seller.order_phone,
                    }
                )
                context["seller_communication_form"] = seller_communication_form
                # Load the form that was submitted.
                seller_about_us_form = SellerAboutUsForm(request.POST)
                context["seller_about_us_form"] = seller_about_us_form
                if seller_about_us_form.is_valid():
                    save_model = None
                    if (
                        seller_about_us_form.cleaned_data.get("about_us")
                        != request.user.user_group.seller.about_us
                    ):
                        request.user.user_group.seller.about_us = (
                            seller_about_us_form.cleaned_data.get("about_us")
                        )
                        save_model = request.user.user_group.seller
                else:
                    raise InvalidFormError(
                        seller_about_us_form, "Invalid SellerAboutUsForm"
                    )
            if save_model:
                save_model.save()
                messages.success(request, "Successfully saved!")
            else:
                messages.info(request, "No changes detected.")
            # This is an HTMX request, so respond with html snippet
            if request.headers.get("HX-Request"):
                return render(
                    request, "supplier_dashboard/company_settings.html", context
                )
            else:
                return render(
                    request, "supplier_dashboard/company_settings.html", context
                )
        except InvalidFormError as e:
            # This will let bootstrap know to highlight the fields with errors.
            for field in e.form.errors:
                e.form[field].field.widget.attrs["class"] += " is-invalid"
            # messages.error(request, "Error saving, please contact us if this continues.")
            # messages.error(request, e.msg)
    else:
        form = SellerForm(
            initial={
                "company_name": request.user.user_group.seller.name,
                "company_phone": request.user.user_group.seller.phone,
                "website": request.user.user_group.seller.website,
                "company_logo": request.user.user_group.seller.location_logo_url,
            }
        )
        context["form"] = form
        seller_communication_form = SellerCommunicationForm(
            initial={
                "dispatch_email": request.user.user_group.seller.order_email,
                "dispatch_phone": request.user.user_group.seller.order_phone,
            }
        )
        context["seller_communication_form"] = seller_communication_form
        seller_about_us_form = SellerAboutUsForm(
            initial={"about_us": request.user.user_group.seller.about_us}
        )
        context["seller_about_us_form"] = seller_about_us_form
    return render(request, "supplier_dashboard/company_settings.html", context)


@login_required(login_url="/admin/login/")
def bookings(request):
    link_params = {}
    if request.method == "POST":
        if request.POST.get("service_date", None) is not None:
            link_params["service_date"] = request.POST.get("service_date")
        if request.POST.get("location_id", None) is not None:
            link_params["location_id"] = request.POST.get("location_id")
    elif request.method == "GET":
        if request.GET.get("service_date", None) is not None:
            link_params["service_date"] = request.GET.get("service_date")
        if request.GET.get("location_id", None) is not None:
            link_params["location_id"] = request.GET.get("location_id")
    # non_pending_cutoff = datetime.date.today() - datetime.timedelta(days=60)
    context = {}
    # context["user"] = request.user
    if not request.session.get("seller"):
        request.session["seller"] = to_dict(request.user.user_group.seller)
    context["seller"] = request.session["seller"]
    seller = Seller.objects.get(id=context["seller"]["id"])
    orders = Order.objects.filter(
        order_group__seller_product_seller_location__seller_product__seller_id=context[
            "seller"
        ]["id"]
    )
    if link_params.get("service_date", None) is not None:
        orders = orders.filter(end_date=link_params["service_date"])
    if link_params.get("location_id", None) is not None:
        orders = orders.filter(
            order_group__seller_product_seller_location__seller_location_id=link_params[
                "location_id"
            ]
        )
    # context["non_pending_cutoff"] = non_pending_cutoff
    context["pending_count"] = 0
    context["scheduled_count"] = 0
    context["complete_count"] = 0
    context["cancelled_count"] = 0
    for order in orders:
        if order.status == Order.PENDING:
            context["pending_count"] += 1
        # if order.end_date >= non_pending_cutoff:
        elif order.status == Order.SCHEDULED:
            context["scheduled_count"] += 1
        elif order.status == Order.COMPLETE:
            context["complete_count"] += 1
        elif order.status == Order.CANCELLED:
            context["cancelled_count"] += 1
    context["status_complete_link"] = seller.get_dashboard_status_url(
        Order.COMPLETE, snippet_name="table_status_orders", **link_params
    )
    context["status_cancelled_link"] = seller.get_dashboard_status_url(
        Order.CANCELLED, snippet_name="table_status_orders", **link_params
    )
    context["status_scheduled_link"] = seller.get_dashboard_status_url(
        Order.SCHEDULED, snippet_name="table_status_orders", **link_params
    )
    context["status_pending_link"] = seller.get_dashboard_status_url(
        Order.PENDING, snippet_name="table_status_orders", **link_params
    )
    # print(context["status_pending_link"])
    return render(request, "supplier_dashboard/bookings.html", context)


@login_required(login_url="/admin/login/")
def update_order_status(request, order_id, accept=True):
    context = {}
    service_date = None
    if request.method == "POST":
        if request.POST.get("queryParams", None) is not None:
            queryParams = request.POST.get("queryParams")
            params = parse_qs(queryParams)
            if params.get("service_date"):
                service_date = params["service_date"][0]
    elif request.method == "GET":
        if request.GET.get("queryParams", None) is not None:
            queryParams = request.GET.get("queryParams")
            params = parse_qs(queryParams)
            if params.get("service_date"):
                service_date = params["service_date"][0]
    try:
        order = Order.objects.get(id=order_id)
        context["order"] = order
        if order.status == Order.PENDING:
            if accept:
                order.status = Order.SCHEDULED
                order.save()
                if request.session.get("seller"):
                    seller_id = request.session["seller"]["id"]
                else:
                    seller_id = (
                        order.order_group.seller_product_seller_location.seller_product.seller_id
                    )
                request.session["seller"] = to_dict(request.user.user_group.seller)
                context["seller"] = request.session["seller"]
                # non_pending_cutoff = datetime.date.today() - datetime.timedelta(days=60)
                orders = Order.objects.filter(
                    order_group__seller_product_seller_location__seller_product__seller_id=seller_id
                )
                if service_date:
                    orders = orders.filter(end_date=service_date)
                # orders = orders.filter(Q(status=Order.SCHEDULED) | Q(status=Order.PENDING))
                pending_count = 0
                scheduled_count = 0
                complete_count = 0
                cancelled_count = 0
                for order in orders:
                    if order.status == Order.PENDING:
                        pending_count += 1
                    # if order.end_date >= non_pending_cutoff:
                    elif order.status == Order.SCHEDULED:
                        scheduled_count += 1
                    elif order.status == Order.COMPLETE:
                        complete_count += 1
                    elif order.status == Order.CANCELLED:
                        cancelled_count += 1
                # TODO: Add toast that shows the order with a link to see it.
                context[
                    "oob_html"
                ] = f"""
                <span id="pending-count-badge" hx-swap-oob="true">{pending_count}</span>
                <span id="scheduled-count-badge" hx-swap-oob="true">{scheduled_count}</span>
                <span id="complete-count-badge" hx-swap-oob="true">{complete_count}</span>
                <span id="cancelled-count-badge" hx-swap-oob="true">{cancelled_count}</span>
                """
            else:
                # Send internal email to notify of denial.
                internal_email.supplier_denied_order(order)
    except Exception as e:
        logger.error(f"update_order_status: [{e}]", exc_info=e)
        return render(
            request,
            "notifications/emails/failover_email_us.html",
            {"subject": f"Supplier%20Approved%20%5B{order_id}%5D"},
        )
    if request.method == "POST":
        # if request.headers.get("HX-Request"): # This is an HTMX request, so respond with html snippet
        context["forloop"] = {"counter": request.POST.get("loopcount", 0)}
        return render(
            request,
            "supplier_dashboard/snippets/table_row_order_update.html",
            context,
        )
    else:
        # This is a GET request, so render a full success page.
        return render(
            request,
            "notifications/emails/supplier_order_updated.html",
            {"order_id": order_id},
        )


@login_required(login_url="/admin/login/")
def update_booking_status(request, order_id, accept=True):
    context = {}
    try:
        order = Order.objects.get(id=order_id)
        context["order"] = order
        if order.status == Order.PENDING:
            if accept:
                order.status = Order.SCHEDULED
                order.save()
                context["oob_html"] = (
                    f"""<p id="booking-status" hx-swap-oob="true">{order.status}</p>"""
                )
            else:
                # Send internal email to notify of denial.
                internal_email.supplier_denied_order(order)
    except Exception as e:
        logger.error(f"update_booking_status: [{e}]", exc_info=e)
        return render(
            request,
            "notifications/emails/failover_email_us.html",
            {"subject": f"Supplier%20Approved%20%5B{order_id}%5D"},
        )
    if request.method == "POST":
        # if request.headers.get("HX-Request"): # This is an HTMX request, so respond with html snippet
        return render(
            request,
            "supplier_dashboard/snippets/order_status.html",
            context,
        )
    else:
        return render(
            request,
            "supplier_dashboard/snippets/order_status.html",
            context,
        )


@login_required(login_url="/admin/login/")
def booking_detail(request, order_id):
    context = {}
    # context["user"] = request.user
    if not request.session.get("seller"):
        request.session["seller"] = to_dict(request.user.user_group.seller)
    order = Order.objects.filter(id=order_id)
    order = order.select_related(
        "order_group__seller_product_seller_location__seller_product__seller",
        "order_group__user_address",
        "order_group__user",
        "order_group__seller_product_seller_location__seller_product__product__main_product",
    )
    order = order.prefetch_related(
        "payouts", "seller_invoice_payable_line_items"
    ).first()
    context["order"] = order
    return render(request, "supplier_dashboard/booking_detail.html", context)


@login_required(login_url="/admin/login/")
def payouts(request):
    context = {}
    location_id = None
    if request.method == "POST":
        location_id = request.POST.get("location_id", None)
    elif request.method == "GET":
        location_id = request.GET.get("location_id", None)
    # context["user"] = request.user
    # NOTE: Can add stuff to session if needed to speed up queries.
    if not request.session.get("seller"):
        request.session["seller"] = to_dict(request.user.user_group.seller)
    orders = Order.objects.filter(order_group__user_id=request.user.id)
    if location_id:
        orders = orders.filter(
            order_group__seller_product_seller_location__seller_location_id=location_id
        )
    orders = orders.prefetch_related("payouts").order_by("-end_date")
    sunday = datetime.date.today() - datetime.timedelta(
        days=datetime.date.today().weekday()
    )
    context["payouts"] = []
    context["total_paid"] = 0
    context["paid_this_week"] = 0
    context["not_yet_paid"] = 0
    for order in orders:
        total_paid = order.total_paid_to_seller()
        context["total_paid"] += total_paid
        context["not_yet_paid"] += order.needed_payout_to_seller()
        if order.start_date >= sunday:
            context["paid_this_week"] += total_paid
        context["payouts"].extend([p for p in order.payouts.all()])
    return render(request, "supplier_dashboard/payouts.html", context)


@login_required(login_url="/admin/login/")
def payout_detail(request, payout_id):
    # NOTE: Can add stuff to session if needed to speed up queries.
    payout = None
    if not payout:
        payout = Payout.objects.get(id=payout_id)
    context = {}
    context["user"] = request.user
    # context["seller"] = request.user.user_group.seller
    # TODO: Check if this is a checkbook payout (this changes with LOB integration).
    if payout.checkbook_payout_id:
        context["related_payouts"] = Payout.objects.filter(
            checkbook_payout_id=payout.checkbook_payout_id
        )
    context["payout"] = payout
    return render(request, "supplier_dashboard/payout_detail.html", context)


@login_required(login_url="/admin/login/")
def locations(request):
    context = {}
    # context["user"] = request.user
    if not request.session.get("seller"):
        request.session["seller"] = to_dict(request.user.user_group.seller)
    seller_locations = SellerLocation.objects.filter(
        seller_id=request.session["seller"]["id"]
    )
    context["seller_locations"] = seller_locations
    return render(request, "supplier_dashboard/locations.html", context)


@login_required(login_url="/admin/login/")
def location_detail(request, location_id):
    context = {}
    # context["user"] = request.user
    if not request.session.get("seller"):
        request.session["seller"] = to_dict(request.user.user_group.seller)
    seller_location = SellerLocation.objects.get(id=location_id)
    context["seller_location"] = seller_location
    orders = (
        Order.objects.filter(order_group__user_id=request.user.id)
        .filter(
            order_group__seller_product_seller_location__seller_location_id=location_id
        )
        .prefetch_related("payouts")
        .order_by("-end_date")
    )
    context["orders"] = []
    context["payouts"] = []
    # Only show the last 5 orders, and add a "View All" link.
    for order in orders:
        context["orders"].append(order)
        context["payouts"].extend([p for p in order.payouts.all()])
    context["orders"] = context["orders"][:5]
    context["payouts"] = context["payouts"][:5]
    if request.method == "POST":
        try:
            save_model = None
            if "compliance_submit" in request.POST:
                # Load other forms so template has complete data.
                seller_payout_initial = {
                    "payee_name": seller_location.payee_name,
                }
                if hasattr(seller_location, "mailing_address"):
                    seller_payout_initial.update(
                        {
                            "street": seller_location.mailing_address.street,
                            "city": seller_location.mailing_address.city,
                            "state": seller_location.mailing_address.state,
                            "postal_code": seller_location.mailing_address.postal_code,
                        }
                    )
                payout_form = SellerPayoutForm(initial=seller_payout_initial)
                # Load the form that was submitted.
                form = SellerLocationComplianceForm(request.POST, request.FILES)
                context["compliance_form"] = form
                if form.is_valid():
                    if request.FILES.get("gl_coi"):
                        seller_location.gl_coi = request.FILES["gl_coi"]
                        save_model = seller_location
                    if (
                        form.cleaned_data.get("gl_coi_expiration_date")
                        != seller_location.gl_coi_expiration_date
                    ):
                        seller_location.gl_coi_expiration_date = form.cleaned_data.get(
                            "gl_coi_expiration_date"
                        )
                        save_model = seller_location
                    if request.FILES.get("auto_coi"):
                        seller_location.auto_coi = request.FILES["auto_coi"]
                        save_model = seller_location
                    if (
                        form.cleaned_data.get("auto_coi_expiration_date")
                        != seller_location.auto_coi_expiration_date
                    ):
                        seller_location.auto_coi_expiration_date = (
                            form.cleaned_data.get("auto_coi_expiration_date")
                        )
                        save_model = seller_location
                    if request.FILES.get("workers_comp_coi"):
                        seller_location.workers_comp_coi = request.FILES[
                            "workers_comp_coi"
                        ]
                        save_model = seller_location
                    if (
                        form.cleaned_data.get("workers_comp_coi_expiration_date")
                        != seller_location.workers_comp_coi_expiration_date
                    ):
                        seller_location.workers_comp_coi_expiration_date = (
                            form.cleaned_data.get("workers_comp_coi_expiration_date")
                        )
                        save_model = seller_location
                    if request.FILES.get("w9"):
                        seller_location.w9 = request.FILES["w9"]
                        save_model = seller_location
                else:
                    raise InvalidFormError(form, "Invalid SellerLocationComplianceForm")
            elif "payout_submit" in request.POST:
                # Load other forms so template has complete data.
                compliance_form = SellerLocationComplianceForm(
                    initial={
                        "gl_coi": seller_location.gl_coi,
                        "gl_coi_expiration_date": seller_location.gl_coi_expiration_date,
                        "auto_coi": seller_location.auto_coi,
                        "auto_coi_expiration_date": seller_location.auto_coi_expiration_date,
                        "workers_comp_coi": seller_location.workers_comp_coi,
                        "workers_comp_coi_expiration_date": seller_location.workers_comp_coi_expiration_date,
                        "w9": seller_location.w9,
                    }
                )
                context["compliance_form"] = compliance_form
                # Load the form that was submitted.
                payout_form = SellerPayoutForm(request.POST)
                context["payout_form"] = payout_form
                if payout_form.is_valid():
                    save_model = None
                    if not hasattr(seller_location, "mailing_address"):
                        mailing_address = SellerLocationMailingAddress(
                            seller_location_id=seller_location.id,
                            street=payout_form.cleaned_data.get("street"),
                            city=payout_form.cleaned_data.get("city"),
                            state=payout_form.cleaned_data.get("state"),
                            postal_code=payout_form.cleaned_data.get("postal_code"),
                            country="US",
                        )
                        mailing_address.save()
                        save_model = mailing_address
                        if (
                            payout_form.cleaned_data.get("payee_name")
                            != seller_location.payee_name
                        ):
                            seller_location.payee_name = payout_form.cleaned_data.get(
                                "payee_name"
                            )
                            seller_location.save()
                    else:
                        if (
                            payout_form.cleaned_data.get("payee_name")
                            != seller_location.payee_name
                        ):
                            seller_location.payee_name = payout_form.cleaned_data.get(
                                "payee_name"
                            )
                            seller_location.save()
                            save_model = seller_location.mailing_address
                        if (
                            payout_form.cleaned_data.get("street")
                            != seller_location.mailing_address.street
                        ):
                            seller_location.mailing_address.street = (
                                payout_form.cleaned_data.get("street")
                            )
                            save_model = seller_location.mailing_address
                        if (
                            payout_form.cleaned_data.get("city")
                            != seller_location.mailing_address.city
                        ):
                            seller_location.mailing_address.city = (
                                payout_form.cleaned_data.get("city")
                            )
                            save_model = seller_location.mailing_address
                        if (
                            payout_form.cleaned_data.get("state")
                            != seller_location.mailing_address.state
                        ):
                            seller_location.mailing_address.state = (
                                payout_form.cleaned_data.get("state")
                            )
                            save_model = seller_location.mailing_address
                        if (
                            payout_form.cleaned_data.get("postal_code")
                            != seller_location.mailing_address.postal_code
                        ):
                            seller_location.mailing_address.postal_code = (
                                payout_form.cleaned_data.get("postal_code")
                            )
                            save_model = seller_location.mailing_address
                else:
                    raise InvalidFormError(payout_form, "Invalid SellerPayoutForm")

            if save_model:
                save_model.save()
                messages.success(request, "Successfully saved!")
            else:
                messages.info(request, "No changes detected.")
            # if request.headers.get("HX-Request"): Could handle htmx here.
            return render(request, "supplier_dashboard/location_detail.html", context)
        except InvalidFormError as e:
            # This will let bootstrap know to highlight the fields with errors.
            for field in e.form.errors:
                e.form[field].field.widget.attrs["class"] += " is-invalid"
            # messages.error(request, "Error saving, please contact us if this continues.")
            # messages.error(request, e.msg)
    else:
        compliance_form = SellerLocationComplianceForm(
            initial={
                "gl_coi": seller_location.gl_coi,
                "gl_coi_expiration_date": seller_location.gl_coi_expiration_date,
                "auto_coi": seller_location.auto_coi,
                "auto_coi_expiration_date": seller_location.auto_coi_expiration_date,
                "workers_comp_coi": seller_location.workers_comp_coi,
                "workers_comp_coi_expiration_date": seller_location.workers_comp_coi_expiration_date,
                "w9": seller_location.w9,
            }
        )
        context["compliance_form"] = compliance_form
        seller_payout_initial = {
            "payee_name": seller_location.payee_name,
        }
        if hasattr(seller_location, "mailing_address"):
            seller_payout_initial.update(
                {
                    "street": seller_location.mailing_address.street,
                    "city": seller_location.mailing_address.city,
                    "state": seller_location.mailing_address.state,
                    "postal_code": seller_location.mailing_address.postal_code,
                }
            )
        payout_form = SellerPayoutForm(initial=seller_payout_initial)
        context["payout_form"] = payout_form

    return render(request, "supplier_dashboard/location_detail.html", context)


@login_required(login_url="/admin/login/")
def received_invoices(request):
    context = {}
    # context["user"] = request.user
    if not request.session.get("seller"):
        request.session["seller"] = to_dict(request.user.user_group.seller)
    invoices = SellerInvoicePayable.objects.filter(
        seller_location__seller_id=request.session["seller"]["id"]
    ).order_by("-invoice_date")
    context["seller_invoice_payables"] = invoices
    return render(request, "supplier_dashboard/received_invoices.html", context)


@login_required(login_url="/admin/login/")
def received_invoice_detail(request, invoice_id):
    context = {}
    # context["user"] = request.user
    if not request.session.get("seller"):
        request.session["seller"] = to_dict(request.user.user_group.seller)
    invoice = SellerInvoicePayable.objects.get(id=invoice_id)
    # invoice_line_items = invoice.seller_invoice_payable_line_items.all()
    invoice_line_items = SellerInvoicePayableLineItem.objects.filter(
        seller_invoice_payable_id=invoice_id
    )
    context["seller_invoice_payable"] = invoice
    if invoice.invoice_file.name.endswith(".pdf"):
        context["is_pdf"] = True
    else:
        context["is_pdf"] = False
    context["seller_invoice_payable_line_items"] = invoice_line_items
    return render(request, "supplier_dashboard/received_invoice_detail.html", context)


@api_view(["GET"])
@authentication_classes([])
@permission_classes([])
def supplier_digest_dashboard(request, supplier_id, status: str = None):
    key = request.query_params.get("key", "")
    snippet_name = request.query_params.get("snippet_name", "accordian_status_orders")
    service_date = request.query_params.get("service_date", None)
    location_id = request.query_params.get("location_id", None)
    try:
        params = decrypt_string(key)
        if str(params) == str(supplier_id):
            context = {}
            # non_pending_cutoff = datetime.date.today() - datetime.timedelta(days=60)
            if status:
                orders = Order.objects.filter(
                    order_group__seller_product_seller_location__seller_product__seller_id=supplier_id
                ).filter(status=status.upper())
                # TODO: Check the delay for a seller with large number of orders, like Hillen.
                # if status.upper() != Order.PENDING:
                #     orders = orders.filter(end_date__gt=non_pending_cutoff)
                if service_date:
                    orders = orders.filter(end_date=service_date)
                if location_id:
                    orders = orders.filter(
                        order_group__seller_product_seller_location__seller_location_id=location_id
                    )
                # Select related fields to reduce db queries.
                orders = orders.select_related(
                    "order_group__seller_product_seller_location__seller_product__seller",
                    "order_group__user_address",
                )
                orders = orders.order_by("-end_date")
                context["status"] = {"name": status.upper(), "orders": orders}

                return render(
                    request,
                    f"supplier_dashboard/snippets/{snippet_name}.html",
                    context,
                )
            else:
                context["status_list"] = []
                supplier = Seller.objects.get(id=supplier_id)
                # NOTE: To include orders in this view, simply add them to the status_list.
                # orders = Order.objects.filter(
                #     order_group__seller_product_seller_location__seller_product__seller_id=supplier_id
                # ).filter(status=Order.PENDING)
                # # .filter(Q(status=Order.PENDING) | Q(status=Order.SCHEDULED))
                # # Select related fields to reduce db queries.
                # orders = orders.select_related(
                #     "order_group__seller_product_seller_location__seller_product__seller",
                #     "order_group__user_address",
                # ).order_by("-end_date")
                #
                # context["status_list"].append({"name": "PENDING", "orders": orders})
                context["seller"] = supplier
                context["status_complete_link"] = supplier.get_dashboard_status_url(
                    Order.COMPLETE
                )
                context["status_cancelled_link"] = supplier.get_dashboard_status_url(
                    Order.CANCELLED
                )
                context["status_scheduled_link"] = supplier.get_dashboard_status_url(
                    Order.SCHEDULED
                )
                context["status_pending_link"] = supplier.get_dashboard_status_url(
                    Order.PENDING
                )

                return render(request, "supplier_dashboard/dailydigest.html", context)
        else:
            raise ValueError("Invalid Token")
    except Exception as e:
        logger.error(f"supplier_digest_dashboard: [{e}]", exc_info=e)
        return render(
            request,
            "notifications/emails/failover_email_us.html",
            {"subject": f"Supplier%20Digest%20Error%20%5B{supplier_id}%5D"},
        )
