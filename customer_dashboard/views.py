from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from typing import List
import json
import uuid
from django.contrib import messages
from django.contrib.auth import logout
from urllib.parse import parse_qs, urlencode
import datetime
from itertools import chain
from django.http import HttpResponse, HttpResponseRedirect, HttpRequest
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

from .forms import UserForm

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


def get_seller(request: HttpRequest):
    if request.session.get("seller"):
        seller = request.session["seller"]
    else:
        if request.user.is_staff:
            # TODO: If staff, then set seller to all available sellers
            try:
                # Temporarily set to Hillen as default
                seller = to_dict(
                    Seller.objects.get(id="73937cad-c1aa-4657-af30-45c4984efbe6")
                )
            except Seller.DoesNotExist:
                # Fails on DEV, so see if we can get user's seller.
                if hasattr(request.user, "user_group") and hasattr(
                    request.user.user_group, "seller"
                ):
                    seller = to_dict(request.user.user_group.seller)
                    request.session["seller"] = seller
                else:
                    # Get first available seller.
                    seller = to_dict(Seller.objects.all().first())
            request.session["seller"] = seller
        elif hasattr(request.user, "user_group") and hasattr(
            request.user.user_group, "seller"
        ):
            seller = to_dict(request.user.user_group.seller)
            request.session["seller"] = seller
        else:
            return HttpResponse("Not Allowed", status=403)
            # return HttpResponseRedirect("/admin/login/")

    return seller


########################
# Page views
########################
# Add redirect to auth0 login if not logged in.
def customer_logout(request):
    logout(request)
    # Redirect to a success page.
    return HttpResponseRedirect("https://trydownstream.com/")


@login_required(login_url="/admin/login/")
def customer_search(request):
    context = {}
    if request.method == "POST":
        search = request.POST.get("search")
        try:
            seller_id = uuid.UUID(search)
            sellers = Seller.objects.filter(id=seller_id)
        except ValueError:
            sellers = Seller.objects.filter(name__icontains=search)
        context["sellers"] = sellers

    return render(
        request, "customer_dashboard/snippets/seller_search_list.html", context
    )


@login_required(login_url="/admin/login/")
def customer_select(request):
    if request.method == "POST":
        seller_id = request.POST.get("seller_id")
    elif request.method == "GET":
        seller_id = request.GET.get("seller_id")
    else:
        return HttpResponse("Not Implemented", status=406)
    try:
        seller = Seller.objects.get(id=seller_id)
        request.session["seller"] = to_dict(seller)
        return HttpResponseRedirect("/customer/")
    except Exception as e:
        return HttpResponse("Not Found", status=404)


@login_required(login_url="/admin/login/")
def index(request):
    context = {}
    # context["user"] = request.user
    # context["seller"] = get_seller(request)
    # orders = Order.objects.filter(
    #     order_group__seller_product_seller_location__seller_product__seller_id=context[
    #         "seller"
    #     ]["id"]
    # )
    # orders = orders.select_related(
    #     "order_group__seller_product_seller_location__seller_product__seller",
    #     "order_group__user_address",
    #     "order_group__user",
    #     "order_group__seller_product_seller_location__seller_product__product__main_product",
    # )
    # orders = orders.prefetch_related("payouts", "order_line_items")
    # # .filter(status=Order.PENDING)
    # context["earnings"] = 0
    # earnings_by_category = {}
    # pending_count = 0
    # scheduled_count = 0
    # complete_count = 0
    # cancelled_count = 0
    # earnings_by_month = [0] * 12
    # for order in orders:
    #     context["earnings"] += float(order.seller_price())
    #     earnings_by_month[order.end_date.month - 1] += float(order.seller_price())

    #     category = (
    #         order.order_group.seller_product_seller_location.seller_product.product.main_product.main_product_category.name
    #     )
    #     if category not in earnings_by_category:
    #         earnings_by_category[category] = {"amount": 0, "percent": 0}
    #     earnings_by_category[category]["amount"] += float(order.seller_price())

    #     if order.status == Order.PENDING:
    #         pending_count += 1
    #     elif order.status == Order.SCHEDULED:
    #         scheduled_count += 1
    #     elif order.status == Order.COMPLETE:
    #         complete_count += 1
    #     elif order.status == Order.CANCELLED:
    #         cancelled_count += 1

    # # # Just test data here
    # # earnings_by_category["Business Dumpster"] = {"amount": 2000, "percent": 0}
    # # earnings_by_category["Junk Removal"] = {"amount": 5000, "percent": 0}
    # # earnings_by_category["Scissor Lift"] = {"amount": 100, "percent": 0}
    # # earnings_by_category["Concrete & Masonary"] = {
    # #     "amount": 50,
    # #     "percent": 0,
    # # }
    # # earnings_by_category["Office Unit"] = {"amount": 25, "percent": 0}
    # # earnings_by_category["Forklift"] = {"amount": 80, "percent": 0}
    # # earnings_by_category["Boom Lifts"] = {"amount": 800, "percent": 0}
    # # context["earnings"] += 200 + 500 + 100 + 50 + 25 + 80 + 800

    # # Sort the dictionary by the 'amount' field in descending order
    # sorted_categories = sorted(
    #     earnings_by_category.items(), key=lambda x: x[1]["amount"], reverse=True
    # )

    # # Calculate the 'percent' field for each category
    # for category, data in sorted_categories:
    #     data["percent"] = int((data["amount"] / context["earnings"]) * 100)

    # # Create a new category 'Other' for the categories that are not in the top 4
    # other_amount = sum(data["amount"] for category, data in sorted_categories[4:])
    # other_percent = int((other_amount / context["earnings"]) * 100)

    # # Create the final dictionary
    # final_categories = dict(sorted_categories[:4])
    # final_categories["Other"] = {"amount": other_amount, "percent": other_percent}
    # context["earnings_by_category"] = final_categories
    # # print(final_categories)
    # context["pending_count"] = pending_count
    # seller_locations = SellerLocation.objects.filter(seller_id=context["seller"]["id"])
    # # context["pending_count"] = orders.count()
    # context["location_count"] = seller_locations.count()
    # context["user_count"] = User.objects.filter(
    #     user_group__seller_id=context["seller"]["id"]
    # ).count()

    # context["chart_data"] = json.dumps(get_dashboard_chart_data(earnings_by_month))

    if request.headers.get("HX-Request"):
        context["page_title"] = "Dashboard"
        return render(request, "customer_dashboard/snippets/dashboard.html", context)
    else:
        return render(request, "customer_dashboard/index.html", context)


@login_required(login_url="/admin/login/")
def profile(request):
    context = {}
    context["user"] = request.user
    context["seller"] = get_seller(request)

    if request.method == "POST":
        # NOTE: Since email is disabled, it is never POSTed,
        # so we need to copy the POST data and add the email back in. This ensures its presence in the form.
        POST_COPY = request.POST.copy()
        POST_COPY["email"] = request.user.email
        form = UserForm(POST_COPY, request.FILES)
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
            if request.FILES.get("photo"):
                request.user.photo = request.FILES["photo"]
                save_db = True
            elif request.POST.get("photo-clear") == "on":
                request.user.photo = None
                save_db = True
            if save_db:
                context["user"] = request.user
                request.user.save()
                messages.success(request, "Successfully saved!")
            else:
                messages.info(request, "No changes detected.")
            # Reload the form with the updated data (for some reason it doesn't update the form with the POST data).
            form = UserForm(
                initial={
                    "first_name": request.user.first_name,
                    "last_name": request.user.last_name,
                    "phone": request.user.phone,
                    "photo": request.user.photo,
                    "email": request.user.email,
                }
            )
            context["form"] = form
            # return HttpResponse("", status=200)
            # This is an HTMX request, so respond with html snippet
            # if request.headers.get("HX-Request"):
            return render(request, "customer_dashboard/profile.html", context)
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
                "photo": request.user.photo,
                "email": request.user.email,
            }
        )
        context["form"] = form
    return render(request, "customer_dashboard/profile.html", context)


def messages_clear(request):
    """Clear the Django messages currently displayed on the page."""
    return HttpResponse("")
