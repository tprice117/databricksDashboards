import csv
import datetime
import logging
import uuid
from itertools import chain
from typing import List, Union
from urllib.parse import parse_qs, urlencode

import humanize
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)

from api.models import (
    Order,
    OrderGroup,
    Payout,
    Seller,
    SellerInvoicePayable,
    SellerInvoicePayableLineItem,
    SellerLocation,
    SellerLocationMailingAddress,
    User,
    UserAddress,
)
from api.models.user.user_group import UserGroup
from api.models.user.user_seller_location import UserSellerLocation
from api.utils.utils import decrypt_string
from chat.models import Conversation, Message
from common.models.choices.user_type import UserType
from common.utils import DistanceUtils
from communications.intercom.utils.utils import get_json_safe_value
from notifications.utils import internal_email

from .forms import (
    ChatMessageForm,
    SellerAboutUsForm,
    SellerCommunicationForm,
    SellerForm,
    SellerLocationComplianceAdminForm,
    SellerLocationComplianceForm,
    SellerPayoutForm,
    UserForm,
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
    for i in range(11, 0, -1):
        months.append(all_months[(current_month - i) % 12])
        data.append(round(data_by_month[(current_month - i) % 12], 2))

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


def is_impersonating(request: HttpRequest) -> bool:
    return request.session.get("user_id") and request.session.get("user_id") != str(
        request.user.id
    )


def get_seller(request: HttpRequest) -> Union[Seller, None]:
    """Returns the current seller. This handles the case where the user is impersonating another user.
    If the user is impersonating, it will return the seller of the impersonated user.
    The the user is staff and is not impersonating a user, then it will return None.

    Args:
        request (HttpRequest): Current request object.

    Returns:
        [Seller, None]: Returns the Seller object or None. None means staff user.
    """
    if is_impersonating(request):
        seller = Seller.objects.get(id=request.session["seller_id"])
    elif request.user.is_staff:
        seller = None
    else:
        # Normal user
        if request.session.get("seller_id"):
            seller = Seller.objects.get(id=request.session["seller_id"])
        else:
            # Cache seller id for faster lookups
            seller = request.user.user_group.seller
            request.session["seller_id"] = get_json_safe_value(seller.id)

    return seller


def get_user(request: HttpRequest) -> User:
    """Returns the current user. This handles the case where the user is impersonating another user.

    Args:
        request (HttpRequest): Current request object.

    Returns:
        dict: Dictionary of the User object.
    """
    if is_impersonating(request):
        user = User.objects.get(id=request.session.get("user_id"))
    else:
        user = request.user
    return user


########################
# Page views
########################
# Add redirect to auth0 login if not logged in.
def supplier_logout(request):
    logout(request)
    # Redirect to a success page.
    return HttpResponseRedirect("https://trydownstream.com/")


@login_required(login_url="/admin/login/")
def supplier_search(request):
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
        request, "supplier_dashboard/snippets/seller_search_list.html", context
    )


@login_required(login_url="/admin/login/")
def supplier_impersonation_start(request):
    if request.user.is_staff:
        if request.method == "POST":
            # user_id = request.POST.get("user_id")
            seller_id = request.POST.get("seller_id")
        elif request.method == "GET":
            # user_id = request.GET.get("user_id")
            seller_id = request.GET.get("seller_id")
        else:
            return HttpResponse("Not Implemented", status=406)
        try:
            seller = Seller.objects.get(id=seller_id)
            user = seller.usergroup.users.filter(type=UserType.ADMIN).first()
            # user = User.objects.get(id=user_id)
            request.session["user_id"] = get_json_safe_value(user.id)
            request.session["seller_id"] = get_json_safe_value(seller_id)
            return HttpResponseRedirect("/supplier/")
        except Exception:
            return HttpResponse("Not Found", status=404)
    else:
        return HttpResponse("Unauthorized", status=401)


@login_required(login_url="/admin/login/")
def supplier_impersonation_stop(request):
    if request.session.get("user_id"):
        del request.session["user_id"]
    if request.session.get("seller_id"):
        del request.session["seller_id"]
    if request.session.get("seller"):
        del request.session["seller"]
    return HttpResponseRedirect("/supplier/")


@login_required(login_url="/admin/login/")
def index(request):
    context = {}
    context["user"] = get_user(request)
    context["seller"] = get_seller(request)

    if request.headers.get("HX-Request"):
        if context["seller"]:
            orders = Order.objects.filter(
                order_group__seller_product_seller_location__seller_product__seller_id=context[
                    "seller"
                ].id
            )
        else:
            orders = Order.objects.all()
        orders = orders.select_related(
            "order_group__seller_product_seller_location__seller_product__seller",
            "order_group__user_address",
            "order_group__user",
            "order_group__seller_product_seller_location__seller_product__product__main_product",
        )
        orders = orders.prefetch_related("payouts", "order_line_items")
        # .filter(status=Order.Status.PENDING)
        context["earnings"] = 0
        earnings_by_category = {}
        pending_count = 0
        scheduled_count = 0
        complete_count = 0
        cancelled_count = 0
        earnings_by_month = [0] * 12
        one_year_ago = datetime.date.today() - datetime.timedelta(days=365)
        for order in orders:
            context["earnings"] += float(order.seller_price())
            if order.end_date >= one_year_ago:
                earnings_by_month[order.end_date.month - 1] += float(
                    order.seller_price()
                )

            category = (
                order.order_group.seller_product_seller_location.seller_product.product.main_product.main_product_category.name
            )
            if category not in earnings_by_category:
                earnings_by_category[category] = {"amount": 0, "percent": 0}
            earnings_by_category[category]["amount"] += float(order.seller_price())

            if order.status == Order.Status.PENDING:
                pending_count += 1
            elif order.status == Order.Status.SCHEDULED:
                scheduled_count += 1
            elif order.status == Order.Status.COMPLETE:
                complete_count += 1
            elif order.status == Order.Status.CANCELLED:
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
            if context["earnings"] == 0:
                data["percent"] = int((data["amount"] / 1) * 100)
            else:
                data["percent"] = int((data["amount"] / context["earnings"]) * 100)

        # Create a new category 'Other' for the categories that are not in the top 4
        other_amount = sum(data["amount"] for category, data in sorted_categories[4:])
        if context["earnings"] == 0:
            other_percent = int((other_amount / 1) * 100)
        else:
            other_percent = int((other_amount / context["earnings"]) * 100)

        # Create the final dictionary
        final_categories = dict(sorted_categories[:4])
        final_categories["Other"] = {"amount": other_amount, "percent": other_percent}
        context["earnings_by_category"] = final_categories
        # print(final_categories)
        context["pending_count"] = pending_count
        if context["seller"]:
            seller_locations = SellerLocation.objects.filter(
                seller_id=context["seller"].id
            )
            seller_users = User.objects.filter(
                user_group__seller_id=context["seller"].id
            )
        else:
            seller_locations = SellerLocation.objects.all()
            seller_users = User.objects.filter(user_group__seller__isnull=False)
        # context["pending_count"] = orders.count()
        context["location_count"] = seller_locations.count()
        context["user_count"] = seller_users.count()

        context["chart_data"] = get_dashboard_chart_data(earnings_by_month)
        return render(request, "supplier_dashboard/snippets/dashboard.html", context)
    else:
        return render(request, "supplier_dashboard/index.html", context)


@login_required(login_url="/admin/login/")
def profile(request):
    context = {}
    context["user"] = get_user(request)
    context["seller"] = get_seller(request)

    if request.method == "POST":
        # NOTE: Since email is disabled, it is never POSTed,
        # so we need to copy the POST data and add the email back in. This ensures its presence in the form.
        POST_COPY = request.POST.copy()
        POST_COPY["email"] = context["user"].email
        form = UserForm(POST_COPY, request.FILES, auth_user=context["user"])
        context["form"] = form
        if form.is_valid():
            save_db = False
            if form.cleaned_data.get("first_name") != context["user"].first_name:
                context["user"].first_name = form.cleaned_data.get("first_name")
                save_db = True
            if form.cleaned_data.get("last_name") != context["user"].last_name:
                context["user"].last_name = form.cleaned_data.get("last_name")
                save_db = True
            if form.cleaned_data.get("phone") != context["user"].phone:
                context["user"].phone = form.cleaned_data.get("phone")
                save_db = True
            if form.cleaned_data.get("type") != context["user"].type:
                context["user"].type = form.cleaned_data.get("type")
                save_db = True
            if request.FILES.get("photo"):
                context["user"].photo = request.FILES["photo"]
                save_db = True
            elif request.POST.get("photo-clear") == "on":
                context["user"].photo = None
                save_db = True
            if save_db:
                context["user"] = context["user"]
                context["user"].save()
                messages.success(request, "Successfully saved!")
            else:
                messages.info(request, "No changes detected.")
            # Reload the form with the updated data (for some reason it doesn't update the form with the POST data).
            form = UserForm(
                initial={
                    "first_name": context["user"].first_name,
                    "last_name": context["user"].last_name,
                    "phone": context["user"].phone,
                    "photo": context["user"].photo,
                    "email": context["user"].email,
                    "type": context["user"].type,
                },
                auth_user=context["user"],
            )
            context["form"] = form
            # return HttpResponse("", status=200)
            # This is an HTMX request, so respond with html snippet
            # if request.headers.get("HX-Request"):
            return render(request, "supplier_dashboard/profile.html", context)
        else:
            # This will let bootstrap know to highlight the fields with errors.
            for field in form.errors:
                form[field].field.widget.attrs["class"] += " is-invalid"
            # messages.error(request, "Error saving, please contact us if this continues.")
    else:
        form = UserForm(
            initial={
                "first_name": context["user"].first_name,
                "last_name": context["user"].last_name,
                "phone": context["user"].phone,
                "photo": context["user"].photo,
                "email": context["user"].email,
                "type": context["user"].type,
            },
            auth_user=context["user"],
        )
        context["form"] = form
    return render(request, "supplier_dashboard/profile.html", context)


@login_required(login_url="/admin/login/")
def company(request):
    context = {}
    context["user"] = get_user(request)
    context["seller"] = get_seller(request)
    if context["seller"]:
        seller = context["seller"]
    else:
        if hasattr(request.user, "user_group") and hasattr(
            request.user.user_group, "seller"
        ):
            seller = request.user.user_group.seller
            messages.warning(
                request,
                f"No seller selected! Using current staff user's seller [{seller.name}].",
            )
        else:
            # Get first available seller.
            seller = Seller.objects.all().first()
            messages.warning(
                request,
                f"No seller selected! Using first seller found: [{seller.name}].",
            )

    if request.method == "POST":
        try:
            save_model = None
            if "company_submit" in request.POST:
                # Load other forms so template has complete data.
                seller_communication_form = SellerCommunicationForm(
                    initial={
                        "dispatch_email": seller.order_email,
                        "dispatch_phone": seller.order_phone,
                    }
                )
                context["seller_communication_form"] = seller_communication_form
                seller_about_us_form = SellerAboutUsForm(
                    initial={"about_us": seller.about_us}
                )
                context["seller_about_us_form"] = seller_about_us_form
                # Load the form that was submitted.
                form = SellerForm(request.POST)
                context["form"] = form
                if form.is_valid():
                    if form.cleaned_data.get("company_name") != seller.name:
                        seller.name = form.cleaned_data.get("company_name")
                        save_model = seller
                    if form.cleaned_data.get("company_phone") != seller.phone:
                        seller.phone = form.cleaned_data.get("company_phone")
                        save_model = seller
                    if form.cleaned_data.get("website") != seller.website:
                        seller.website = form.cleaned_data.get("website")
                        save_model = seller
                    if (
                        form.cleaned_data.get("company_logo")
                        != seller.location_logo_url
                    ):
                        seller.location_logo_url = form.cleaned_data.get("company_logo")
                        save_model = seller
                else:
                    raise InvalidFormError(form, "Invalid SellerForm")
            elif "communication_submit" in request.POST:
                # Load other forms so template has complete data.
                form = SellerForm(
                    initial={
                        "company_name": seller.name,
                        "company_phone": seller.phone,
                        "website": seller.website,
                        "company_logo": seller.location_logo_url,
                    }
                )
                context["form"] = form
                seller_about_us_form = SellerAboutUsForm(
                    initial={"about_us": seller.about_us}
                )
                context["seller_about_us_form"] = seller_about_us_form
                # Load the form that was submitted.
                seller_communication_form = SellerCommunicationForm(request.POST)
                context["seller_communication_form"] = seller_communication_form
                if seller_communication_form.is_valid():
                    save_model = None
                    if (
                        seller_communication_form.cleaned_data.get("dispatch_email")
                        != seller.order_email
                    ):
                        seller.order_email = seller_communication_form.cleaned_data.get(
                            "dispatch_email"
                        )
                        save_model = seller
                    if (
                        seller_communication_form.cleaned_data.get("dispatch_phone")
                        != seller.order_phone
                    ):
                        seller.order_phone = seller_communication_form.cleaned_data.get(
                            "dispatch_phone"
                        )
                        save_model = seller
                else:
                    raise InvalidFormError(
                        seller_communication_form, "Invalid SellerCommunicationForm"
                    )
            elif "about_us_submit" in request.POST:
                # Load other forms so template has complete data.
                form = SellerForm(
                    initial={
                        "company_name": seller.name,
                        "company_phone": seller.phone,
                        "website": seller.website,
                        "company_logo": seller.location_logo_url,
                    }
                )
                context["form"] = form
                seller_communication_form = SellerCommunicationForm(
                    initial={
                        "dispatch_email": seller.order_email,
                        "dispatch_phone": seller.order_phone,
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
                        != seller.about_us
                    ):
                        seller.about_us = seller_about_us_form.cleaned_data.get(
                            "about_us"
                        )
                        save_model = seller
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
                "company_name": seller.name,
                "company_phone": seller.phone,
                "website": seller.website,
                "company_logo": seller.location_logo_url,
            }
        )
        context["form"] = form
        seller_communication_form = SellerCommunicationForm(
            initial={
                "dispatch_email": seller.order_email,
                "dispatch_phone": seller.order_phone,
            }
        )
        context["seller_communication_form"] = seller_communication_form
        seller_about_us_form = SellerAboutUsForm(initial={"about_us": seller.about_us})
        context["seller_about_us_form"] = seller_about_us_form
    return render(request, "supplier_dashboard/company_settings.html", context)


@login_required(login_url="/admin/login/")
def users(request):
    context = {}
    context["user"] = get_user(request)
    context["seller"] = get_seller(request)
    if context["seller"]:
        seller = context["seller"]
    else:
        if hasattr(request.user, "user_group") and hasattr(
            request.user.user_group, "seller"
        ):
            seller = request.user.user_group.seller
            messages.warning(
                request,
                f"No seller selected! Using current staff user's seller [{seller.name}].",
            )
        else:
            # Get first available seller.
            seller = Seller.objects.all().first()
            messages.warning(
                request,
                f"No seller selected! Using first seller found: [{seller.name}].",
            )
    pagination_limit = 25
    page_number = 1
    if request.GET.get("p", None) is not None:
        page_number = request.GET.get("p")
    # user_id = request.GET.get("user_id", None)
    date = request.GET.get("date", None)
    # This is an HTMX request, so respond with html snippet
    # if request.headers.get("HX-Request"):
    query_params = request.GET.copy()
    users = User.objects.filter(user_group_id=context["user"].user_group_id)
    if date:
        users = users.filter(date_joined__date=date)
    users = users.order_by("-date_joined")

    user_lst = []
    for user in users:
        user_dict = {}
        user_dict["user"] = user
        user_dict["meta"] = {
            "associated_locations": UserAddress.objects.filter(user_id=user.id).count()
        }
        user_lst.append(user_dict)

    paginator = Paginator(user_lst, pagination_limit)
    page_obj = paginator.get_page(page_number)
    context["page_obj"] = page_obj

    if page_number is None:
        page_number = 1
    else:
        page_number = int(page_number)

    query_params["p"] = 1
    context["page_start_link"] = (
        f"{reverse('supplier_users')}?{query_params.urlencode()}"
    )
    query_params["p"] = page_number
    context["page_current_link"] = (
        f"{reverse('supplier_users')}?{query_params.urlencode()}"
    )
    if page_obj.has_previous():
        query_params["p"] = page_obj.previous_page_number()
        context["page_prev_link"] = (
            f"{reverse('supplier_users')}?{query_params.urlencode()}"
        )
    if page_obj.has_next():
        query_params["p"] = page_obj.next_page_number()
        context["page_next_link"] = (
            f"{reverse('supplier_users')}?{query_params.urlencode()}"
        )
    query_params["p"] = paginator.num_pages
    context["page_end_link"] = f"{reverse('supplier_users')}?{query_params.urlencode()}"
    return render(request, "supplier_dashboard/users.html", context)


@login_required(login_url="/admin/login/")
def user_detail(request, user_id):
    context = {}
    auth_user = get_user(request)
    context["seller"] = get_seller(request)
    # This is an HTMX request, so respond with html snippet
    # if request.headers.get("HX-Request"):
    user = User.objects.get(id=user_id)
    context["user"] = user
    user_seller_locations = UserSellerLocation.objects.filter(
        user_id=context["user"].id
    ).select_related("user")

    context["user_seller_locations"] = user_seller_locations
    if user.user_group_id:
        order_groups = OrderGroup.objects.filter(user_id=user.id)
        # Select related fields to reduce db queries.
        order_groups = order_groups.select_related(
            "seller_product_seller_location__seller_product__seller",
            "seller_product_seller_location__seller_product__product__main_product",
            # "user_address",
        )
        # order_groups = order_groups.prefetch_related("orders")
        order_groups = order_groups.order_by("-end_date")

        today = datetime.date.today()
        context["active_orders"] = []
        context["past_orders"] = []
        for order_group in order_groups:
            if order_group.end_date and order_group.end_date < today:
                if len(context["past_orders"]) < 2:
                    context["past_orders"].append(order_group)
            else:
                if len(context["active_orders"]) < 2:
                    context["active_orders"].append(order_group)
            # Only show the first 2 active and past order_groups.
            if len(context["active_orders"]) >= 2 and len(context["past_orders"]) >= 2:
                break

    if request.method == "POST":
        # NOTE: Since email is disabled, it is never POSTed,
        # so we need to copy the POST data and add the email back in. This ensures its presence in the form.
        POST_COPY = request.POST.copy()
        POST_COPY["email"] = user.email
        form = UserForm(POST_COPY, request.FILES, auth_user=auth_user, user=user)
        context["form"] = form
        if form.is_valid():
            save_db = False
            if form.cleaned_data.get("first_name") != user.first_name:
                user.first_name = form.cleaned_data.get("first_name")
                save_db = True
            if form.cleaned_data.get("last_name") != user.last_name:
                user.last_name = form.cleaned_data.get("last_name")
                save_db = True
            if form.cleaned_data.get("phone") != user.phone:
                user.phone = form.cleaned_data.get("phone")
                save_db = True
            if form.cleaned_data.get("type") != user.type:
                user.type = form.cleaned_data.get("type")
                save_db = True
            if request.FILES.get("photo"):
                user.photo = request.FILES["photo"]
                save_db = True
            elif request.POST.get("photo-clear") == "on":
                user.photo = None
                save_db = True
            if save_db:
                context["user"] = user
                user.save()
                messages.success(request, "Successfully saved!")
            else:
                messages.info(request, "No changes detected.")
            # Reload the form with the updated data (for some reason it doesn't update the form with the POST data).
            form = UserForm(
                initial={
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "phone": user.phone,
                    "photo": user.photo,
                    "email": user.email,
                    "type": user.type,
                },
                auth_user=auth_user,
                user=user,
            )
            context["form"] = form
            # return HttpResponse("", status=200)
            # This is an HTMX request, so respond with html snippet
            # if request.headers.get("HX-Request"):
            return render(request, "supplier_dashboard/user_detail.html", context)
        else:
            # This will let bootstrap know to highlight the fields with errors.
            for field in form.errors:
                form[field].field.widget.attrs["class"] += " is-invalid"
            # messages.error(request, "Error saving, please contact us if this continues.")
    else:
        form = UserForm(
            initial={
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone": user.phone,
                "photo": user.photo,
                "email": user.email,
                "type": user.type,
            },
            auth_user=auth_user,
            user=user,
        )
        context["form"] = form

    return render(request, "supplier_dashboard/user_detail.html", context)


@login_required(login_url="/admin/login/")
def new_user(request):
    context = {}
    # TODO: Only allow admin to create new users.
    context["user"] = get_user(request)
    context["seller"] = get_seller(request)
    if request.method == "POST":
        try:
            save_model = None
            POST_COPY = request.POST.copy()
            # POST_COPY["email"] = user.email
            form = UserForm(POST_COPY, request.FILES, auth_user=context["user"])
            context["form"] = form
            context["form"].fields["email"].disabled = False
            if form.is_valid():
                first_name = form.cleaned_data.get("first_name")
                last_name = form.cleaned_data.get("last_name")
                phone = form.cleaned_data.get("phone")
                email = form.cleaned_data.get("email")
                user_type = form.cleaned_data.get("type")
                user = User(
                    user_group_id=context["user"].user_group_id,
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    type=user_type,
                )
                if phone:
                    user.phone = phone
                if request.FILES.get("photo"):
                    user.photo = request.FILES["photo"]
                save_model = user
            else:
                raise InvalidFormError(form, "Invalid UserForm")
            if save_model:
                save_model.save()
                messages.success(request, "Successfully saved!")
            else:
                messages.info(request, "No changes detected.")
            return HttpResponseRedirect(reverse("supplier_users"))
        except InvalidFormError as e:
            # This will let bootstrap know to highlight the fields with errors.
            for field in e.form.errors:
                e.form[field].field.widget.attrs["class"] += " is-invalid"
    else:
        context["form"] = UserForm(auth_user=context["user"])
        context["form"].fields["email"].required = True
        context["form"].fields["email"].disabled = False

    return render(request, "supplier_dashboard/user_new_edit.html", context)


@login_required(login_url="/admin/login/")
def bookings(request):
    link_params = {}
    context = {}
    pagination_limit = 25
    page_number = 1
    context["user"] = get_user(request)
    context["seller"] = get_seller(request)
    ordering = ["-end_date"]
    if request.GET.get("service_date", None) is not None:
        link_params["service_date"] = request.GET.get("service_date")
    if request.GET.get("o", None) is not None and request.GET.get("o", None) != "":
        link_params["o"] = request.GET.get("o")  # o=-end_date.submitted_on
        ordering = link_params["o"].split(".")
    if request.GET.get("location_id", None) is not None:
        link_params["location_id"] = request.GET.get("location_id")
    if request.GET.get("p", None) is not None:
        page_number = request.GET.get("p")
    # This is an HTMX request, so respond with html snippet
    if request.headers.get("HX-Request"):
        query_params = request.GET.copy()
        # Ensure tab is valid. Default to PENDING if not.
        tab = request.GET.get("tab", Order.Status.PENDING)
        if tab.upper() not in [
            Order.Status.PENDING,
            Order.Status.SCHEDULED,
            Order.Status.COMPLETE,
            Order.Status.CANCELLED,
        ]:
            tab = Order.Status.PENDING
        tab_status = tab.upper()
        if context["seller"]:
            orders = Order.objects.filter(
                order_group__seller_product_seller_location__seller_product__seller_id=context[
                    "seller"
                ].id
            )

            if not request.user.is_staff:
                orders = orders.filter(submitted_on__isnull=False)
        else:
            orders = Order.objects.all()

        # orders = orders.filter(status=tab_status)
        # TODO: Check the delay for a seller with large number of orders, like Hillen.
        # if status.upper() != Order.Status.PENDING:
        #     orders = orders.filter(end_date__gt=non_pending_cutoff)
        if link_params.get("service_date", None) is not None:
            orders = orders.filter(end_date=link_params["service_date"])
        if link_params.get("location_id", None) is not None:
            orders = orders.filter(
                order_group__seller_product_seller_location__seller_location_id=link_params[
                    "location_id"
                ]
            )
        # Select related fields to reduce db queries.
        orders = orders.select_related(
            "order_group__seller_product_seller_location__seller_product__seller",
            "order_group__user_address",
        )
        orders = orders.order_by(*ordering)
        status_orders = []
        # Return the correct counts for each status.
        pending_count = 0
        scheduled_count = 0
        complete_count = 0
        cancelled_count = 0
        for order in orders:
            if order.status == tab_status:
                status_orders.append(order)
            if order.status == Order.Status.PENDING:
                pending_count += 1
            # if order.end_date >= non_pending_cutoff:
            elif order.status == Order.Status.SCHEDULED:
                scheduled_count += 1
            elif order.status == Order.Status.COMPLETE:
                complete_count += 1
            elif order.status == Order.Status.CANCELLED:
                cancelled_count += 1

        download_link = f"/supplier/bookings/download/?{query_params.urlencode()}"
        context["download_link"] = download_link
        context[
            "oob_html"
        ] = f"""
        <span id="pending-count-badge" hx-swap-oob="true">{pending_count}</span>
        <span id="scheduled-count-badge" hx-swap-oob="true">{scheduled_count}</span>
        <span id="complete-count-badge" hx-swap-oob="true">{complete_count}</span>
        <span id="cancelled-count-badge" hx-swap-oob="true">{cancelled_count}</span>
        <a id="bookings-download-csv" class="btn btn-primary btn-sm d-none d-sm-inline-block" role="button" href="{download_link}" hx-swap-oob="true"><i class="fas fa-download fa-sm text-white-50"></i>&nbsp;Generate CSV</a>
        """

        paginator = Paginator(status_orders, pagination_limit)
        page_obj = paginator.get_page(page_number)
        context["status"] = {
            "name": tab_status,
            "page_obj": page_obj,
        }
        context["page_obj"] = page_obj
        context["pages"] = []

        if page_number is None:
            page_number = 1
        else:
            page_number = int(page_number)

        query_params["p"] = 1
        context["page_start_link"] = f"/supplier/bookings/?{query_params.urlencode()}"
        query_params["p"] = page_number
        context["page_current_link"] = f"/supplier/bookings/?{query_params.urlencode()}"
        if page_obj.has_previous():
            query_params["p"] = page_obj.previous_page_number()
            context["page_prev_link"] = (
                f"/supplier/bookings/?{query_params.urlencode()}"
            )
        if page_obj.has_next():
            query_params["p"] = page_obj.next_page_number()
            context["page_next_link"] = (
                f"/supplier/bookings/?{query_params.urlencode()}"
            )
        query_params["p"] = paginator.num_pages
        context["page_end_link"] = f"/supplier/bookings/?{query_params.urlencode()}"

        return render(
            request, "supplier_dashboard/snippets/table_status_orders.html", context
        )
    else:
        # non_pending_cutoff = datetime.date.today() - datetime.timedelta(days=60)
        if context["seller"]:
            orders = Order.objects.filter(
                order_group__seller_product_seller_location__seller_product__seller_id=context[
                    "seller"
                ].id
            )
        else:
            orders = Order.objects.all()
        if link_params.get("service_date", None) is not None:
            orders = orders.filter(end_date=link_params["service_date"])
        if link_params.get("location_id", None) is not None:
            orders = orders.filter(
                order_group__seller_product_seller_location__seller_location_id=link_params[
                    "location_id"
                ]
            )
        # To optimize, we can use values_list to get only the status field.
        orders = orders.values_list("status", flat=True)
        # context["non_pending_cutoff"] = non_pending_cutoff
        context["pending_count"] = 0
        context["scheduled_count"] = 0
        context["complete_count"] = 0
        context["cancelled_count"] = 0
        for status in orders:
            if status == Order.Status.PENDING:
                context["pending_count"] += 1
            elif status == Order.Status.SCHEDULED:
                context["scheduled_count"] += 1
            elif status == Order.Status.COMPLETE:
                context["complete_count"] += 1
            elif status == Order.Status.CANCELLED:
                context["cancelled_count"] += 1
        query_params = ""
        if link_params:
            query_params = f"&{urlencode(link_params)}"
        context["status_pending_link"] = (
            f"/supplier/bookings/?tab={Order.Status.PENDING}{query_params}"
        )
        context["status_complete_link"] = (
            f"/supplier/bookings/?tab={Order.Status.COMPLETE}{query_params}"
        )
        context["status_cancelled_link"] = (
            f"/supplier/bookings/?tab={Order.Status.CANCELLED}{query_params}"
        )
        context["status_scheduled_link"] = (
            f"/supplier/bookings/?tab={Order.Status.SCHEDULED}{query_params}"
        )
        url_query_params = request.GET.copy()
        context["download_link"] = (
            f"/supplier/bookings/download/?{url_query_params.urlencode()}"
        )
        # If current link has a tab, then load full path
        if url_query_params.get("tab", None) is not None:
            tab = url_query_params["tab"]
            if tab == Order.Status.COMPLETE:
                tab = "-completed"
            elif tab == Order.Status.PENDING:
                tab = ""
            else:
                tab = f"-{tab.lower()}"
            context["htmx_loading_id"] = f"htmx-indicator-status{tab}"
            context["status_load_link"] = request.get_full_path()
        else:
            # Else load pending tab as default
            context["htmx_loading_id"] = "htmx-indicator-status"
            context["status_load_link"] = (
                f"/supplier/bookings/?tab={Order.Status.PENDING}{query_params}"
            )
        return render(request, "supplier_dashboard/bookings.html", context)


@login_required(login_url="/admin/login/")
def download_bookings(request):
    link_params = {}
    context = {}
    context["user"] = get_user(request)
    context["seller"] = get_seller(request)
    ordering = ["-end_date"]
    if request.GET.get("service_date", None) is not None:
        link_params["service_date"] = request.GET.get("service_date")
    if request.GET.get("o", None) is not None and request.GET.get("o", None) != "":
        link_params["o"] = request.GET.get("o")  # o=-end_date.submitted_on
        ordering = link_params["o"].split(".")
    if request.GET.get("location_id", None) is not None:
        link_params["location_id"] = request.GET.get("location_id")
    # Ensure tab is valid. Default to PENDING if not.
    tab = request.GET.get("tab", Order.Status.PENDING)
    if tab.upper() not in [
        Order.Status.PENDING,
        Order.Status.SCHEDULED,
        Order.Status.COMPLETE,
        Order.Status.CANCELLED,
    ]:
        tab = Order.Status.PENDING
    if context["seller"]:
        orders = Order.objects.filter(
            order_group__seller_product_seller_location__seller_product__seller_id=context[
                "seller"
            ].id
        )
    else:
        orders = Order.objects.all()

    orders = orders.filter(status=tab)

    if link_params.get("service_date", None) is not None:
        orders = orders.filter(end_date=link_params["service_date"])
    if link_params.get("location_id", None) is not None:
        orders = orders.filter(
            order_group__seller_product_seller_location__seller_location_id=link_params[
                "location_id"
            ]
        )
    # Select related fields to reduce db queries.
    orders = orders.select_related(
        "order_group__seller_product_seller_location__seller_product__seller",
        "order_group__user_address",
    )
    orders = orders.order_by(*ordering)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="orders_{tab.lower()}.csv"'
    writer = csv.writer(response)
    if request.user.is_staff:
        header_row = [
            "Seller",
            "Service Date",
            "Product",
            "Booking Address",
            "Type",
            "Status",
            "Time Since Order",
        ]
    else:
        header_row = ["Service Date", "Product", "Booking Address", "Type", "Status"]
    writer.writerow(header_row)
    now_time = timezone.now()
    for order in orders:
        row = [
            order.end_date.strftime("%Y-%m-%d"),
            str(
                order.order_group.seller_product_seller_location.seller_product.product.main_product.name
            ),
            order.order_group.user_address.formatted_address(),
            str(order.order_type),
            str(order.status),
        ]
        if request.user.is_staff:
            row.insert(
                0,
                order.order_group.seller_product_seller_location.seller_location.seller.name,
            )
            if order.submitted_on:
                row.append(humanize.naturaldelta(now_time - order.submitted_on))
            else:
                row.append("Not Submitted")
        writer.writerow(row)
    return response


@login_required(login_url="/admin/login/")
def update_order_status(request, order_id, accept=True, complete=False):
    context = {}
    context["seller"] = get_seller(request)
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
        if (
            order.status == Order.Status.PENDING
            or order.status == Order.Status.SCHEDULED
        ):
            if accept or complete:
                if accept:
                    order.status = Order.Status.SCHEDULED
                else:
                    order.status = Order.Status.COMPLETE
                order.save()
                # non_pending_cutoff = datetime.date.today() - datetime.timedelta(days=60)
                if context["seller"]:
                    orders = Order.objects.filter(
                        order_group__seller_product_seller_location__seller_product__seller_id=context[
                            "seller"
                        ].id
                    )
                else:
                    orders = Order.objects.all()
                if service_date:
                    orders = orders.filter(end_date=service_date)
                # orders = orders.filter(Q(status=Order.Status.SCHEDULED) | Q(status=Order.Status.PENDING))
                # To optimize, we can use values_list to get only the status field.
                orders = orders.values_list("status", flat=True)
                pending_count = 0
                scheduled_count = 0
                complete_count = 0
                cancelled_count = 0
                for status in orders:
                    if status == Order.Status.PENDING:
                        pending_count += 1
                    # if order.end_date >= non_pending_cutoff:
                    elif status == Order.Status.SCHEDULED:
                        scheduled_count += 1
                    elif status == Order.Status.COMPLETE:
                        complete_count += 1
                    elif status == Order.Status.CANCELLED:
                        cancelled_count += 1
                # TODO: Add toast that shows the order with a link to see it.
                # https://getbootstrap.com/docs/5.3/components/toasts/
                context[
                    "oob_html"
                ] = f"""
                <span id="pending-count-badge" hx-swap-oob="true">{pending_count}</span>
                <span id="scheduled-count-badge" hx-swap-oob="true">{scheduled_count}</span>
                <span id="complete-count-badge" hx-swap-oob="true">{complete_count}</span>
                <span id="cancelled-count-badge" hx-swap-oob="true">{cancelled_count}</span>
                """
            elif accept is False:
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
def update_booking_status(request, order_id):
    context = {}
    update_status = Order.Status.PENDING
    if request.method == "POST":
        update_status = request.POST.get("status", Order.Status.PENDING)
    elif request.method == "GET":
        update_status = request.GET.get("status", Order.Status.PENDING)
    try:
        order = Order.objects.get(id=order_id)
        context["order"] = order
        if (
            order.status == Order.Status.PENDING
            and update_status == Order.Status.SCHEDULED
        ):
            order.status = Order.Status.SCHEDULED
            order.save()
            context["oob_html"] = (
                f"""<p id="booking-status" hx-swap-oob="true">{order.status}</p>"""
            )
        elif (
            order.status == Order.Status.SCHEDULED
            and update_status == Order.Status.COMPLETE
        ):
            order.status = Order.Status.COMPLETE
            order.save()
            context["oob_html"] = (
                f"""<p id="booking-status" hx-swap-oob="true">{order.status}</p>"""
            )
        elif (
            order.status == Order.Status.PENDING
            and update_status == Order.Status.CANCELLED
        ):
            # Send internal email to notify of denial.
            internal_email.supplier_denied_order(order)
    except Exception as e:
        logger.error(f"update_booking_status: [{e}]", exc_info=e)
        return render(
            request,
            "notifications/emails/failover_email_us.html",
            {"subject": f"Supplier%20Approved%20%5B{order_id}%5D"},
        )
    # if request.headers.get("HX-Request"): # This is an HTMX request, so respond with html snippet
    return render(
        request,
        "supplier_dashboard/snippets/booking_detail_actions.html",
        context,
    )


@login_required(login_url="/admin/login/")
def booking_detail(request, order_id):
    context = {}
    context["user"] = get_user(request)
    context["seller"] = get_seller(request)
    if request.headers.get("HX-Request"):
        lat1 = request.GET.get("lat1", None)
        lon1 = request.GET.get("lon1", None)
        lat2 = request.GET.get("lat2", None)
        lon2 = request.GET.get("lon2", None)
        if lat1 and lon1 and lat2 and lon2:
            context["distance"] = DistanceUtils.get_driving_distance(
                lat1, lon1, lat2, lon2
            )
            return render(
                request,
                "supplier_dashboard/snippets/booking_detail_distance.html",
                context,
            )
    else:
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
        seller_location = (
            order.order_group.seller_product_seller_location.seller_location
        )
        user_address = order.order_group.user_address
        # context["distance"] = DistanceUtils.get_driving_distance(
        #     seller_location.latitude,
        #     seller_location.longitude,
        #     user_address.latitude,
        #     user_address.longitude,
        # )
        query_params = request.GET.copy()
        query_params["lat1"] = seller_location.latitude
        query_params["lon1"] = seller_location.longitude
        query_params["lat2"] = user_address.latitude
        query_params["lon2"] = user_address.longitude
        context["distance_link"] = (
            f"{ reverse('supplier_booking_detail', kwargs={'order_id': order.id}) }?{query_params.urlencode()}"
        )
        line_types = {}
        for order_line_item in order.order_line_items.all():
            try:
                line_types[order_line_item.order_line_item_type.code]["items"].append(
                    order_line_item
                )
            except KeyError:
                line_types[order_line_item.order_line_item_type.code] = {
                    "type": order_line_item.order_line_item_type,
                    "items": [order_line_item],
                }
        # Sort line_types by type["sort"] and put into a list
        context["line_types"] = sorted(
            line_types.values(), key=lambda item: item["type"].sort
        )
        return render(request, "supplier_dashboard/booking_detail.html", context)


@login_required(login_url="/admin/login/")
def chat(request, conversation_id):
    if request.method == "POST":
        message_form = ChatMessageForm(request.POST)

        conversation = Conversation.objects.get(id=conversation_id)

        if message_form.is_valid():
            print("Message form is valid")
            new_message = Message(
                conversation=conversation,
                user=get_user(request),
                message=message_form.cleaned_data.get("message"),
            )
            new_message.save()
        else:
            print("Message form is not valid")
            print(message_form.errors)

    conversation = Conversation.objects.get(id=conversation_id)

    # Create/update the last read time for the current user.
    conversation.view_conversation(
        current_user=get_user(request),
    )

    # Pass the messages in reverse order so that the most recent message is at the bottom of the chat.
    messages_sorted_most_recent = conversation.messages.order_by("created_on")

    # For each message, add a boolean to indicate if the message was sent by the current user.
    for message in messages_sorted_most_recent:
        message.sent_by_current_user = message.user == get_user(request)

    return render(
        request,
        "supplier_dashboard/chat.html",
        {
            "conversation": conversation,
            "messages": messages_sorted_most_recent,
            "message_form": ChatMessageForm(),
        },
    )


@login_required(login_url="/admin/login/")
def payouts(request):
    context = {}
    pagination_limit = 25
    page_number = 1
    if request.GET.get("p", None) is not None:
        page_number = request.GET.get("p")
    location_id = None
    if request.method == "GET":
        location_id = request.GET.get("location_id", None)
    service_date = request.GET.get("service_date", None)
    context["user"] = get_user(request)
    context["seller"] = get_seller(request)
    # This is an HTMX request, so respond with html snippet
    if request.headers.get("HX-Request"):
        if context["seller"]:
            payouts = Payout.objects.filter(
                order__order_group__seller_product_seller_location__seller_product__seller_id=context[
                    "seller"
                ].id
            )
        else:
            payouts = Payout.objects.all()
        if location_id:
            payouts = payouts.filter(
                order__order_group__seller_product_seller_location__seller_location_id=location_id
            )
        if service_date:
            # filter orders by their payouts created_on date
            payouts = payouts.filter(created_on__date=service_date)
        if context["seller"] is None:
            payouts = payouts.select_related(
                "order__order_group__seller_product_seller_location__seller_location__seller"
            )
            payouts = payouts.order_by(
                "order__order_group__seller_product_seller_location__seller_location__seller__name",
                "-created_on",
            )
        else:
            payouts = payouts.order_by("-created_on")
        # print(payouts.count())
        paginator = Paginator(payouts, pagination_limit)
        page_obj = paginator.get_page(page_number)
        context["page_obj"] = page_obj

        query_params = request.GET.copy()
        context["download_link"] = (
            f"/supplier/payouts/download/?{query_params.urlencode()}"
        )
        if page_number is None:
            page_number = 1
        else:
            page_number = int(page_number)

        query_params["p"] = 1
        context["page_start_link"] = (
            f"{reverse('supplier_payouts')}?{query_params.urlencode()}"
        )
        query_params["p"] = page_number
        context["page_current_link"] = (
            f"{reverse('supplier_payouts')}?{query_params.urlencode()}"
        )
        if page_obj.has_previous():
            query_params["p"] = page_obj.previous_page_number()
            context["page_prev_link"] = (
                f"{reverse('supplier_payouts')}?{query_params.urlencode()}"
            )
        if page_obj.has_next():
            query_params["p"] = page_obj.next_page_number()
            context["page_next_link"] = (
                f"{reverse('supplier_payouts')}?{query_params.urlencode()}"
            )
        query_params["p"] = paginator.num_pages
        context["page_end_link"] = (
            f"{reverse('supplier_payouts')}?{query_params.urlencode()}"
        )
        return render(
            request, "supplier_dashboard/snippets/payouts_table.html", context
        )

    query_params = request.GET.copy()
    context["download_link"] = f"/supplier/payouts/download/?{query_params.urlencode()}"
    context["payouts_cards_link"] = (
        f"{reverse('supplier_payouts_metrics')}?{query_params.urlencode()}"
    )
    context["payouts_table_link"] = (
        f"{reverse('supplier_payouts')}?{query_params.urlencode()}"
    )
    return render(request, "supplier_dashboard/payouts.html", context)


@login_required(login_url="/admin/login/")
def payouts_metrics(request):
    if request.method == "GET":
        location_id = request.GET.get("location_id", None)
    service_date = request.GET.get("service_date", None)
    context = {}
    # NOTE: Can add stuff to session if needed to speed up queries.
    context["user"] = get_user(request)
    context["seller"] = get_seller(request)
    if context["seller"]:
        orders = Order.objects.filter(
            order_group__seller_product_seller_location__seller_product__seller_id=context[
                "seller"
            ].id
        )
    else:
        orders = Order.objects.all()
    if location_id:
        orders = orders.filter(
            order_group__seller_product_seller_location__seller_location_id=location_id
        )
    # TODO: Ask if filter should be here, or in the loop below.
    # The difference is the total_paid, paid_this_week, and not_yet_paid values.
    # if service_date:
    #     # filter orders by their payouts created_on date
    #     orders = orders.filter(payouts__created_on__date=service_date)
    orders = orders.prefetch_related("order_line_items")
    if context["seller"] is None:
        orders = orders.select_related(
            "order_group__seller_product_seller_location__seller_location__seller"
        )
        orders = orders.order_by(
            "order_group__seller_product_seller_location__seller_location__seller__name",
            "-end_date",
        )
    else:
        orders = orders.order_by("-end_date")
    sunday = datetime.date.today() - datetime.timedelta(
        days=datetime.date.today().weekday()
    )
    context["total_paid"] = 0
    context["paid_this_week"] = 0
    context["not_yet_paid"] = 0
    for order in orders:
        total_paid = order.total_paid_to_seller()
        context["total_paid"] += total_paid
        context["not_yet_paid"] += order.needed_payout_to_seller()
        if order.start_date >= sunday:
            context["paid_this_week"] += total_paid
    return render(
        request, "supplier_dashboard/snippets/payouts_metric_cards.html", context
    )


@login_required(login_url="/admin/login/")
def payout_invoice(request, payout_id):
    context = {}
    # NOTE: Can add stuff to session if needed to speed up queries.
    context["user"] = get_user(request)
    context["seller"] = get_seller(request)
    payout = Payout.objects.filter(id=payout_id).select_related("order").first()
    order_line_item = payout.order.order_line_items.all().first()
    context["is_pdf"] = False
    if order_line_item:
        # TODO: Add support for check once LOB is integrated.
        stripe_invoice = order_line_item.get_invoice()
        if stripe_invoice:
            # hosted_invoice_url
            context["hosted_invoice_url"] = stripe_invoice.hosted_invoice_url
            context["invoice_pdf"] = stripe_invoice.invoice_pdf
            context["is_pdf"] = True
    return render(
        request, "supplier_dashboard/snippets/payout_detail_invoice.html", context
    )


@login_required(login_url="/admin/login/")
def payout_detail(request, payout_id):
    context = {}
    # NOTE: Can add stuff to session if needed to speed up queries.
    context["user"] = get_user(request)
    context["seller"] = get_seller(request)
    payout = None
    if not payout:
        payout = Payout.objects.get(id=payout_id)
    # TODO: Check if this is a checkbook payout (this changes with LOB integration).
    if payout.checkbook_payout_id:
        context["related_payouts"] = Payout.objects.filter(
            checkbook_payout_id=payout.checkbook_payout_id
        )
    context["payout"] = payout
    return render(request, "supplier_dashboard/payout_detail.html", context)


# Create view that creates csv from payout data and returns it as a download
@login_required(login_url="/admin/login/")
def download_payouts(request):
    context = {}
    if request.method == "GET":
        location_id = request.GET.get("location_id", None)
    service_date = request.GET.get("service_date", None)
    context["user"] = get_user(request)
    context["seller"] = get_seller(request)
    if context["seller"]:
        orders = Order.objects.filter(
            order_group__seller_product_seller_location__seller_product__seller_id=context[
                "seller"
            ].id
        )
    else:
        orders = Order.objects.all()
    if location_id:
        orders = orders.filter(
            order_group__seller_product_seller_location__seller_location_id=location_id
        )
    # TODO: Ask if filter should be here, or in the loop below.
    # The difference is the total_paid, paid_this_week, and not_yet_paid values.
    # if service_date:
    #     # filter orders by their payouts created_on date
    #     orders = orders.filter(payouts__created_on__date=service_date)
    orders = orders.prefetch_related("payouts", "order_line_items")
    if context["seller"] is None:
        orders = orders.select_related(
            "order_group__seller_product_seller_location__seller_location__seller"
        )
        orders = orders.order_by(
            "order_group__seller_product_seller_location__seller_location__seller__name",
            "-end_date",
        )
    else:
        orders = orders.order_by("-end_date")
    payouts = []
    for order in orders:
        if service_date:
            payouts_query = order.payouts.filter(created_on__date=service_date)
        else:
            payouts_query = order.payouts.all()
        if context["seller"] is None:
            payouts_query = payouts_query.select_related(
                "order__order_group__seller_product_seller_location__seller_location__seller"
            )
        payouts.extend([p for p in order.payouts.all()])

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="payouts.csv"'
    writer = csv.writer(response)
    # TODO: After switching to LOB, add checkbook payout id and url.
    if request.user.is_staff:
        header_row = ["Seller", "Payout ID", "Order ID", "Amount", "Created On"]
    else:
        header_row = ["Payout ID", "Order ID", "Amount", "Created On"]
    writer.writerow(header_row)
    for payout in payouts:
        row = []
        if request.user.is_staff:
            row.append(
                payout.order.order_group.seller_product_seller_location.seller_location.seller.name
            )
        row.extend(
            [
                str(payout.id),
                str(payout.order_id),
                str(payout.amount),
                payout.created_on.ctime(),
                # str(payout.checkbook_payout_id),
                # str(payout.stripe_transfer_id),
            ]
        )
        writer.writerow(row)
    return response


@login_required(login_url="/admin/login/")
def locations(request):
    context = {}
    context["user"] = get_user(request)
    context["seller"] = get_seller(request)
    pagination_limit = 25
    page_number = 1
    if request.GET.get("p", None) is not None:
        page_number = request.GET.get("p")
    query_params = request.GET.copy()
    # This is an HTMX request, so respond with html snippet
    if request.headers.get("HX-Request"):
        tab = request.GET.get("tab", None)
        if context["seller"]:
            seller_locations = SellerLocation.objects.filter(
                seller_id=context["seller"].id
            )
            seller_locations = seller_locations.order_by("-created_on")
        else:
            seller_locations = SellerLocation.objects.all()
            seller_locations = seller_locations.order_by("seller__name", "-created_on")

        seller_locations_lst = []
        context["tab"] = tab
        context["total_count"] = 0
        context["insurance_missing"] = 0
        context["insurance_expiring"] = 0
        context["payouts_missing"] = 0
        context["tax_missing"] = 0
        context["fully_compliant"] = 0
        for seller_location in seller_locations:
            context["total_count"] += 1
            is_insurance_compliant = seller_location.is_insurance_compliant
            is_tax_compliant = seller_location.is_tax_compliant
            if is_insurance_compliant and is_tax_compliant:
                context["fully_compliant"] += 1
                if tab == "compliant":
                    seller_locations_lst.append(seller_location)
            elif not is_insurance_compliant:
                context["insurance_missing"] += 1
                if tab == "insurance":
                    seller_locations_lst.append(seller_location)
            elif not is_tax_compliant:
                context["tax_missing"] += 1
                if tab == "tax":
                    seller_locations_lst.append(seller_location)
            if seller_location.is_insurance_expiring_soon:
                context["insurance_expiring"] += 1
                if tab == "insurance_expiring":
                    seller_locations_lst.append(seller_location)
            if seller_location.is_payout_setup is False:
                context["payouts_missing"] += 1
                if tab == "payouts":
                    seller_locations_lst.append(seller_location)
            if tab is None or tab == "":
                seller_locations_lst.append(seller_location)

        download_link = f"/supplier/locations/download/?{query_params.urlencode()}"
        context["download_link"] = download_link

        paginator = Paginator(seller_locations_lst, pagination_limit)
        page_obj = paginator.get_page(page_number)
        context["page_obj"] = page_obj

        if page_number is None:
            page_number = 1
        else:
            page_number = int(page_number)

        query_params["p"] = 1
        context["page_start_link"] = f"/supplier/locations/?{query_params.urlencode()}"
        query_params["p"] = page_number
        context["page_current_link"] = (
            f"/supplier/locations/?{query_params.urlencode()}"
        )
        if page_obj.has_previous():
            query_params["p"] = page_obj.previous_page_number()
            context["page_prev_link"] = (
                f"/supplier/locations/?{query_params.urlencode()}"
            )
        if page_obj.has_next():
            query_params["p"] = page_obj.next_page_number()
            context["page_next_link"] = (
                f"/supplier/locations/?{query_params.urlencode()}"
            )
        query_params["p"] = paginator.num_pages
        context["page_end_link"] = f"/supplier/locations/?{query_params.urlencode()}"
        return render(
            request, "supplier_dashboard/snippets/locations_table.html", context
        )

    context["download_link"] = (
        f"/supplier/locations/download/?{query_params.urlencode()}"
    )
    context["status_insurance_link"] = "/supplier/locations/?tab=insurance"
    context["status_payouts_link"] = "/supplier/locations/?tab=payouts"
    context["status_tax_link"] = "/supplier/locations/?tab=tax"
    context["status_insurance_expiring_link"] = (
        "/supplier/locations/?tab=insurance_expiring"
    )
    context["status_compliant_link"] = "/supplier/locations/?tab=compliant"
    # If current link has a tab, then load full path
    context["htmx_loading_id"] = "htmx-indicator-status"
    if query_params.get("tab", None) is not None:
        context["locations_load_link"] = request.get_full_path()
    else:
        # Else load pending tab as default
        context["locations_load_link"] = (
            f"{reverse('supplier_locations')}?{query_params.urlencode()}"
        )
    return render(request, "supplier_dashboard/locations.html", context)


@login_required(login_url="/admin/login/")
def download_locations(request):
    context = {}
    context["user"] = get_user(request)
    context["seller"] = get_seller(request)
    tab = request.GET.get("tab", None)
    if context["seller"]:
        seller_locations = SellerLocation.objects.filter(seller_id=context["seller"].id)
        seller_locations = seller_locations.order_by("-created_on")
    else:
        seller_locations = SellerLocation.objects.all()
        seller_locations = seller_locations.order_by("seller__name", "-created_on")

    seller_locations_lst = []
    for seller_location in seller_locations:
        is_insurance_compliant = seller_location.is_insurance_compliant
        is_tax_compliant = seller_location.is_tax_compliant
        if is_insurance_compliant and is_tax_compliant:
            if tab == "compliant":
                seller_locations_lst.append(seller_location)
        elif not is_insurance_compliant:
            if tab == "insurance":
                seller_locations_lst.append(seller_location)
        elif not is_tax_compliant:
            if tab == "tax":
                seller_locations_lst.append(seller_location)
        if seller_location.is_insurance_expiring_soon:
            if tab == "insurance_expiring":
                seller_locations_lst.append(seller_location)
        if seller_location.is_payout_setup is False:
            if tab == "payouts":
                seller_locations_lst.append(seller_location)
        if tab is None or tab == "":
            seller_locations_lst.append(seller_location)

    response = HttpResponse(content_type="text/csv")
    if tab is None or tab == "":
        tab = "all"
    response["Content-Disposition"] = f'attachment; filename="locations_{tab}.csv"'
    writer = csv.writer(response)
    if request.user.is_staff:
        header_row = [
            "Seller",
            "Name",
            "Address",
            "Payout Method",
            "Insurance",
            "Tax",
            "Created On",
        ]
    else:
        header_row = [
            "Name",
            "Address",
            "Payout Method",
            "Insurance",
            "Tax",
            "Created On",
        ]
    writer.writerow(header_row)
    for seller_location in seller_locations_lst:
        row = []
        if request.user.is_staff:
            row.append(seller_location.seller.name)
        payout_method = "Unset"
        if seller_location.is_payout_setup:
            if seller_location.stripe_connect_account_id:
                payout_method = "Direct Deposit"
            else:
                payout_method = "Check"
        insurance_status = "Insurance Verification Required"
        if seller_location.is_insurance_expiring_soon:
            insurance_status = "Expiring Soon"
        elif seller_location.is_insurance_compliant:
            insurance_status = "Compliant"
        tax_status = "Missing Tax Info"
        if seller_location.is_tax_compliant:
            tax_status = "Compliant"
        row.extend(
            [
                str(seller_location.name),
                seller_location.formatted_address,
                payout_method,
                insurance_status,
                tax_status,
                seller_location.created_on.ctime(),
            ]
        )
        writer.writerow(row)
    return response


@login_required(login_url="/admin/login/")
def location_detail(request, location_id):
    context = {}
    context["user"] = get_user(request)
    context["seller"] = get_seller(request)
    seller_location = SellerLocation.objects.get(id=location_id)
    context["seller_location"] = seller_location
    orders = (
        Order.objects.filter(order_group__user_id=context["user"].id)
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
    if request.user.is_staff:
        compliance_form_class = SellerLocationComplianceAdminForm
    else:
        compliance_form_class = SellerLocationComplianceForm
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
                context["payout_form"] = SellerPayoutForm(initial=seller_payout_initial)
                context["seller_communication_form"] = SellerCommunicationForm(
                    initial={
                        "dispatch_email": seller_location.order_email,
                        "dispatch_phone": seller_location.order_phone,
                    }
                )
                # Load the form that was submitted.
                form = compliance_form_class(request.POST, request.FILES)
                context["compliance_form"] = form
                if form.is_valid():
                    if request.FILES.get("gl_coi"):
                        seller_location.gl_coi = request.FILES["gl_coi"]
                        save_model = seller_location
                    elif request.POST.get("gl_coi-clear") == "on":
                        seller_location.gl_coi = None
                        save_model = seller_location
                    if request.FILES.get("auto_coi"):
                        seller_location.auto_coi = request.FILES["auto_coi"]
                        save_model = seller_location
                    elif request.POST.get("auto_coi-clear") == "on":
                        seller_location.auto_coi = None
                        save_model = seller_location
                    if request.FILES.get("workers_comp_coi"):
                        seller_location.workers_comp_coi = request.FILES[
                            "workers_comp_coi"
                        ]
                        save_model = seller_location
                    elif request.POST.get("workers_comp_coi-clear") == "on":
                        seller_location.workers_comp_coi = None
                        save_model = seller_location
                    if request.FILES.get("w9"):
                        seller_location.w9 = request.FILES["w9"]
                        save_model = seller_location
                    elif request.POST.get("w9-clear") == "on":
                        seller_location.w9 = None
                        save_model = seller_location
                    # Allow editing if user is staff.
                    if request.user.is_staff:
                        if (
                            form.cleaned_data.get("gl_coi_expiration_date")
                            != seller_location.gl_coi_expiration_date
                        ):
                            seller_location.gl_coi_expiration_date = (
                                form.cleaned_data.get("gl_coi_expiration_date")
                            )
                            save_model = seller_location
                        if (
                            form.cleaned_data.get("auto_coi_expiration_date")
                            != seller_location.auto_coi_expiration_date
                        ):
                            seller_location.auto_coi_expiration_date = (
                                form.cleaned_data.get("auto_coi_expiration_date")
                            )
                            save_model = seller_location
                        if (
                            form.cleaned_data.get("workers_comp_coi_expiration_date")
                            != seller_location.workers_comp_coi_expiration_date
                        ):
                            seller_location.workers_comp_coi_expiration_date = (
                                form.cleaned_data.get(
                                    "workers_comp_coi_expiration_date"
                                )
                            )
                            save_model = seller_location
                    # Reload the form with the updated data (for some reason it doesn't update the form with the POST data).
                    compliance_form = compliance_form_class(
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
                else:
                    raise InvalidFormError(form, "Invalid SellerLocationComplianceForm")
            elif "payout_submit" in request.POST:
                # Load other forms so template has complete data.
                context["compliance_form"] = compliance_form_class(
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
                context["seller_communication_form"] = SellerCommunicationForm(
                    initial={
                        "dispatch_email": seller_location.order_email,
                        "dispatch_phone": seller_location.order_phone,
                    }
                )
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
            elif "communication_submit" in request.POST:
                # Load other forms so template has complete data.
                context["compliance_form"] = compliance_form_class(
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
                context["payout_form"] = SellerPayoutForm(initial=seller_payout_initial)
                # Load the form that was submitted.
                seller_communication_form = SellerCommunicationForm(request.POST)
                context["seller_communication_form"] = seller_communication_form
                if seller_communication_form.is_valid():
                    save_model = None
                    if (
                        seller_communication_form.cleaned_data.get("dispatch_email")
                        != seller_location.order_email
                    ):
                        seller_location.order_email = (
                            seller_communication_form.cleaned_data.get("dispatch_email")
                        )
                        save_model = seller_location
                    if (
                        seller_communication_form.cleaned_data.get("dispatch_phone")
                        != seller_location.order_phone
                    ):
                        seller_location.order_phone = (
                            seller_communication_form.cleaned_data.get("dispatch_phone")
                        )
                        save_model = seller_location
                else:
                    raise InvalidFormError(
                        seller_communication_form,
                        "Invalid SellerLocationCommunicationForm",
                    )

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
        context["compliance_form"] = compliance_form_class(
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
        context["payout_form"] = SellerPayoutForm(initial=seller_payout_initial)
        context["seller_communication_form"] = SellerCommunicationForm(
            initial={
                "dispatch_email": seller_location.order_email,
                "dispatch_phone": seller_location.order_phone,
            }
        )

    # For any request type, get the current UserSellerLocation objects.
    user_seller_locations = UserSellerLocation.objects.filter(
        seller_location_id=location_id
    ).select_related("user")

    context["user_seller_locations"] = user_seller_locations

    # Get the list of UserGroup Users that are not already associated with the SellerLocation.
    seller = SellerLocation.objects.get(id=location_id).seller

    if UserGroup.objects.filter(seller=seller).exists():
        user_group = UserGroup.objects.get(seller=seller)
        print(user_group)
        context["non_associated_users"] = User.objects.filter(
            user_group=user_group
        ).exclude(
            id__in=[
                user_seller_location.user.id
                for user_seller_location in user_seller_locations
            ]
        )

    return render(request, "supplier_dashboard/location_detail.html", context)


@login_required(login_url="/admin/login/")
def user_seller_location_add(request, seller_location_id, user_id):

    seller_location = SellerLocation.objects.get(id=seller_location_id)
    user = User.objects.get(id=user_id)

    # Throw error if user is not in the same seller group as the seller location.
    if user.user_group.seller != seller_location.seller:
        return HttpResponse("Unauthorized", status=401)
    else:
        UserSellerLocation.objects.create(
            user=user,
            seller_location=seller_location,
        )
        return redirect(
            reverse(
                "supplier_location_detail",
                kwargs={
                    "location_id": seller_location_id,
                },
            )
        )


@login_required(login_url="/admin/login/")
def user_seller_location_remove(request, seller_location_id, user_id):

    seller_location = SellerLocation.objects.get(id=seller_location_id)
    user = User.objects.get(id=user_id)

    # Throw error if user is not in the same seller group as the seller location.
    if user.user_group.seller != seller_location.seller:
        return HttpResponse("Unauthorized", status=401)
    else:
        UserSellerLocation.objects.filter(
            user=user,
            seller_location=seller_location,
        ).delete()
        return redirect(
            reverse(
                "supplier_location_detail",
                kwargs={
                    "location_id": seller_location_id,
                },
            )
        )


@login_required(login_url="/admin/login/")
def received_invoices(request):
    context = {}
    context["user"] = get_user(request)
    context["seller"] = get_seller(request)
    pagination_limit = 25
    page_number = 1
    if request.GET.get("p", None) is not None:
        page_number = request.GET.get("p")
    service_date = request.GET.get("service_date", None)
    # This is an HTMX request, so respond with html snippet
    # if request.headers.get("HX-Request"):
    query_params = request.GET.copy()
    if context["seller"]:
        invoices = SellerInvoicePayable.objects.filter(
            seller_location__seller_id=context["seller"].id
        )
    else:
        invoices = SellerInvoicePayable.objects.all()
    if service_date:
        invoices = invoices.filter(invoice_date=service_date)
    if context["seller"]:
        invoices = invoices.select_related("seller_location")
        invoices = invoices.order_by("-invoice_date")
    else:
        invoices = invoices.select_related("seller_location__seller")
        invoices = invoices.order_by("seller_location__seller__name", "-invoice_date")
    paginator = Paginator(invoices, pagination_limit)
    page_obj = paginator.get_page(page_number)
    context["page_obj"] = page_obj

    if page_number is None:
        page_number = 1
    else:
        page_number = int(page_number)

    query_params["p"] = 1
    context["page_start_link"] = (
        f"/supplier/received_invoices/?{query_params.urlencode()}"
    )
    query_params["p"] = page_number
    context["page_current_link"] = (
        f"/supplier/received_invoices/?{query_params.urlencode()}"
    )
    if page_obj.has_previous():
        query_params["p"] = page_obj.previous_page_number()
        context["page_prev_link"] = (
            f"/supplier/received_invoices/?{query_params.urlencode()}"
        )
    if page_obj.has_next():
        query_params["p"] = page_obj.next_page_number()
        context["page_next_link"] = (
            f"/supplier/received_invoices/?{query_params.urlencode()}"
        )
    query_params["p"] = paginator.num_pages
    context["page_end_link"] = (
        f"/supplier/received_invoices/?{query_params.urlencode()}"
    )
    return render(request, "supplier_dashboard/received_invoices.html", context)


@login_required(login_url="/admin/login/")
def received_invoice_detail(request, invoice_id):
    context = {}
    context["user"] = get_user(request)
    context["seller"] = get_seller(request)
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


def messages_clear(request):
    """Clear the Django messages currently displayed on the page."""
    return HttpResponse("")


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
                # if status.upper() != Order.Status.PENDING:
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
                # ).filter(status=Order.Status.PENDING)
                # # .filter(Q(status=Order.Status.PENDING) | Q(status=Order.Status.SCHEDULED))
                # # Select related fields to reduce db queries.
                # orders = orders.select_related(
                #     "order_group__seller_product_seller_location__seller_product__seller",
                #     "order_group__user_address",
                # ).order_by("-end_date")
                #
                # context["status_list"].append({"name": "PENDING", "orders": orders})
                context["seller"] = supplier
                context["status_complete_link"] = supplier.get_dashboard_status_url(
                    Order.Status.COMPLETE
                )
                context["status_cancelled_link"] = supplier.get_dashboard_status_url(
                    Order.Status.CANCELLED
                )
                context["status_scheduled_link"] = supplier.get_dashboard_status_url(
                    Order.Status.SCHEDULED
                )
                context["status_pending_link"] = supplier.get_dashboard_status_url(
                    Order.Status.PENDING
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
