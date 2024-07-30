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
from django.utils.dateparse import parse_datetime
from django.db import IntegrityError
from rest_framework.response import Response
from rest_framework import status
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
from common.models.choices.user_type import UserType
from common.utils import DistanceUtils
from communications.intercom.utils.utils import get_json_safe_value
from notifications.utils import internal_email
from admin_approvals.models import UserGroupAdminApprovalUserInvite
from customer_dashboard.forms import UserInviteForm

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

from communications.intercom.contact import Contact as IntercomContact
from communications.intercom.conversation import Conversation as IntercomConversation

logger = logging.getLogger(__name__)


class InvalidFormError(Exception):
    """Exception raised for validation errors in the form."""

    def __init__(self, form, msg):
        self.form = form
        self.msg = msg

    def __str__(self):
        return self.msg


class UserAlreadyExistsError(Exception):
    """Exception raised if User already exists."""

    pass


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


def get_seller_user_objects(request: HttpRequest, user: User, seller: Seller):
    """Returns the users for the current seller.

    If user is:
        - staff, then all users for all of sellers are returned.
        - not staff
            - is admin, then return all users for the seller.
            - not admin, then only users in the logged in user's user group.

    Args:
        request (HttpRequest): Request object from the view.
        user (User): User object.
        seller (Seller): Seller object.

    Returns:
        QuerySet[User]: The users queryset.
    """
    if not user.is_staff and user.type != UserType.ADMIN:
        seller_users = User.objects.filter(user_group_id=user.user_group_id)
    else:
        if seller:
            seller_users = User.objects.filter(user_group__seller_id=seller.id)
        else:
            seller_users = User.objects.filter(user_group__seller__isnull=False)
    return seller_users


def get_booking_objects(
    request: HttpRequest, user: User, seller: Seller, exclude_in_cart=True
):
    """Returns the orders for the current seller.

    If user is:
        - staff, then all orders for all of sellers are returned.
        - not staff
            - is admin, then return all orders for the seller.
            - not admin, then only orders for the seller locations the user is associated with are returned.

    Args:
        request (HttpRequest): Request object from the view.
        user (User): User object.
        seller (Seller): Seller object.

    Returns:
        QuerySet[Order]: The orders queryset.
    """
    if not user.is_staff and user.type != UserType.ADMIN:
        seller_location_ids = (
            UserSellerLocation.objects.filter(user_id=user.id)
            .select_related("seller_location")
            .values_list("seller_location_id", flat=True)
        )
        orders = Order.objects.filter(
            order_group__seller_product_seller_location__seller_location__in=seller_location_ids
        )
    else:
        if seller:
            orders = Order.objects.filter(
                order_group__seller_product_seller_location__seller_product__seller_id=seller.id
            )
        else:
            orders = Order.objects.all()
    if exclude_in_cart:
        orders = orders.filter(submitted_on__isnull=False)
    return orders


def get_payout_objects(request: HttpRequest, user: User, seller: Seller):
    """Returns the payouts for the current seller.

    If user is:
        - staff, then all payouts for all of sellers are returned.
        - not staff
            - is admin, then return all payouts for the seller.
            - not admin, then only payouts for the seller locations the user is associated with are returned.

    Args:
        request (HttpRequest): Request object from the view.
        user (User): User object.
        seller (Seller): Seller object.

    Returns:
        QuerySet[Payout]: The payouts queryset.
    """
    if not user.is_staff and user.type != UserType.ADMIN:
        seller_location_ids = (
            UserSellerLocation.objects.filter(user_id=user.id)
            .select_related("seller_location")
            .values_list("seller_location_id", flat=True)
        )
        payouts = Payout.objects.filter(
            order__order_group__seller_product_seller_location__seller_location__in=seller_location_ids
        )
    else:
        if seller:
            payouts = Payout.objects.filter(
                order__order_group__seller_product_seller_location__seller_product__seller_id=seller.id
            )
        else:
            payouts = Payout.objects.all()
    return payouts


def get_location_objects(request: HttpRequest, user: User, seller: Seller):
    """Returns the locations for the current seller.

    If user is:
        - staff, then all locations for all of sellers are returned.
        - not staff
            - is admin, then return all locations for the seller.
            - not admin, then only locations for the seller locations the user is associated with are returned.

    Args:
        request (HttpRequest): Request object from the view.
        user (User): User object.
        seller (Seller): Seller object.

    Returns:
        QuerySet[Location]: The locations queryset.
    """
    if not user.is_staff and user.type != UserType.ADMIN:
        user_seller_locations = UserSellerLocation.objects.filter(
            user_id=user.id
        ).select_related("seller_location")
        user_seller_locations = user_seller_locations.order_by(
            "-seller_location__created_on"
        )
        seller_locations = [
            user_seller_location.seller_location
            for user_seller_location in user_seller_locations
        ]
    else:
        if seller:
            seller_locations = SellerLocation.objects.filter(seller_id=seller.id)
            seller_locations = seller_locations.order_by("-created_on")
        else:
            seller_locations = SellerLocation.objects.all()
            seller_locations = seller_locations.order_by("seller__name", "-created_on")
    return seller_locations


def get_recieved_invoice_objects(request: HttpRequest, user: User, seller: Seller):
    """Returns the invoices for the current seller.

    If user is:
        - staff, then all invoices for all of sellers are returned.
        - not staff
            - is admin, then return all invoices for the seller.
            - not admin, then only invoices for the seller locations the user is associated with are returned.

    Args:
        request (HttpRequest): Request object from the view.
        user (User): User object.
        seller (Seller): Seller object.

    Returns:
        QuerySet[SellerInvoicePayable]: The invoices queryset.
    """

    if not user.is_staff and user.type != UserType.ADMIN:
        seller_location_ids = (
            UserSellerLocation.objects.filter(user_id=user.id)
            .select_related("seller_location")
            .values_list("seller_location_id", flat=True)
        )
        invoices = SellerInvoicePayable.objects.filter(
            seller_location__in=seller_location_ids
        )
    else:
        if seller:
            invoices = SellerInvoicePayable.objects.filter(
                seller_location__seller_id=seller.id
            )
        else:
            invoices = SellerInvoicePayable.objects.all()
    if request.user.is_staff:
        invoices = invoices.select_related("seller_location__seller")
        invoices = invoices.order_by("seller_location__seller__name", "-invoice_date")
    else:
        invoices = invoices.select_related("seller_location")
        invoices = invoices.order_by("-invoice_date")
    return invoices


########################
# Page views
########################
# Add redirect to auth0 login if not logged in.
def supplier_logout(request):
    logout(request)
    # Redirect to a success page.
    return HttpResponseRedirect("https://trydownstream.com/")


@login_required(login_url="/admin/login/")
def supplier_search(request, is_selection=False):
    context = {}
    if request.method == "POST":
        search = request.POST.get("search")
        search = search.strip()
        if not search:
            return HttpResponse(status=204)
        try:
            seller_id = uuid.UUID(search)
            sellers = Seller.objects.filter(id=seller_id)
        except ValueError:
            sellers = Seller.objects.filter(name__icontains=search)
        context["sellers"] = sellers

    if is_selection:
        return render(
            request, "supplier_dashboard/snippets/seller_search_selection.html", context
        )
    else:
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
            if not user:
                raise User.DoesNotExist
            # user = User.objects.get(id=user_id)
            request.session["user_id"] = get_json_safe_value(user.id)
            request.session["seller_id"] = get_json_safe_value(seller_id)
            return HttpResponseRedirect("/supplier/")
        except User.DoesNotExist:
            messages.error(
                request,
                "No admin user found for seller. Seller must have at least one admin user.",
            )
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
        orders = get_booking_objects(request, context["user"], context["seller"])
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
        seller_locations = get_location_objects(
            request, context["user"], context["seller"]
        )
        seller_users = get_seller_user_objects(
            request, context["user"], context["seller"]
        )
        if is_impersonating(request):
            context["seller_locations_without_payout_info"] = []
            for seller_location in seller_locations:
                if not seller_location.is_payout_setup:
                    context["seller_locations_without_payout_info"].append(
                        seller_location
                    )
        # context["pending_count"] = orders.count()
        if isinstance(seller_locations, list):
            context["location_count"] = len(seller_locations)
        else:
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
        if (
            hasattr(request.user, "user_group")
            and hasattr(request.user.user_group, "seller")
            and request.user.user_group.seller
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

    pagination_limit = 25
    page_number = 1
    if request.GET.get("p", None) is not None:
        page_number = request.GET.get("p")
    # user_id = request.GET.get("user_id", None)
    date = request.GET.get("date", None)
    # This is an HTMX request, so respond with html snippet
    # if request.headers.get("HX-Request"):
    query_params = request.GET.copy()
    users = get_seller_user_objects(request, context["user"], context["seller"])
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
    # TODO: Add a form to select one or more SellerLocations to associate the user with.
    context = {}
    context["user"] = get_user(request)
    context["seller"] = get_seller(request)
    if context["user"].type != UserType.ADMIN:
        messages.error(request, "Only admins can create new users.")
        return HttpResponseRedirect(reverse("supplier_users"))

    if request.method == "POST":
        try:
            save_model = None
            POST_COPY = request.POST.copy()
            form = UserInviteForm(POST_COPY, request.FILES, auth_user=context["user"])
            context["form"] = form
            # Default to the current user's UserGroup.
            user_group_id = context["user"].user_group_id
            if not context["seller"] and request.user.is_staff:
                seller_id = request.POST.get("sellerId")
                if seller_id:
                    user_group = UserGroup.objects.get(seller_id=seller_id)
                    user_group_id = user_group.id
            if form.is_valid():
                first_name = form.cleaned_data.get("first_name")
                last_name = form.cleaned_data.get("last_name")
                email = form.cleaned_data.get("email")
                user_type = form.cleaned_data.get("type")
                # Check if email is already in use.
                if email and User.objects.filter(email=email.casefold()).exists():
                    raise UserAlreadyExistsError()
                else:
                    user_invite = UserGroupAdminApprovalUserInvite(
                        user_group_id=user_group_id,
                        first_name=first_name,
                        last_name=last_name,
                        email=email,
                        type=user_type,
                        redirect_url="/supplier/",
                    )
                    save_model = user_invite
            else:
                raise InvalidFormError(form, "Invalid UserInviteForm")
            if save_model:
                save_model.save()
                messages.success(request, "Successfully saved!")
            else:
                messages.info(request, "No changes detected.")
            return HttpResponseRedirect(reverse("supplier_users"))
        except UserAlreadyExistsError:
            messages.error(request, "User with that email already exists.")
        except InvalidFormError as e:
            # This will let bootstrap know to highlight the fields with errors.
            for field in e.form.errors:
                e.form[field].field.widget.attrs["class"] += " is-invalid"
        except IntegrityError as e:
            if "unique constraint" in str(e):
                messages.error(request, "User with that email already exists.")
            else:
                messages.error(
                    request, "Error saving, please contact us if this continues."
                )
                messages.error(request, f"Database IntegrityError:[{e}]")
        except UserGroup.DoesNotExist:
            messages.error(
                request,
                "Seller does not have a UserGroup, one must be created first.",
            )
        except Exception as e:
            messages.error(
                request, "Error saving, please contact us if this continues."
            )
            messages.error(request, e)
    else:
        context["form"] = UserInviteForm(auth_user=context["user"])

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
        orders = get_booking_objects(
            request, context["user"], context["seller"], exclude_in_cart=False
        )
        query_params = request.GET.copy()
        # Ensure tab is valid. Default to PENDING if not.
        tab = request.GET.get("tab", Order.Status.PENDING)
        if tab.upper() not in [
            Order.Status.PENDING,
            Order.Status.SCHEDULED,
            Order.Status.COMPLETE,
            Order.Status.CANCELLED,
            "CART",
        ]:
            tab = Order.Status.PENDING
        tab_status = tab.upper()
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
        cart_count = 0
        for order in orders:
            if order.submitted_on is None:
                if tab_status == "CART":
                    status_orders.append(order)
            elif order.status == tab_status:
                status_orders.append(order)
            if order.submitted_on is None:
                cart_count += 1
            elif order.status == Order.Status.PENDING:
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
        <span id="cart-count-badge" hx-swap-oob="true">{cart_count}</span>
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
        orders = get_booking_objects(request, context["user"], context["seller"])
        # non_pending_cutoff = datetime.date.today() - datetime.timedelta(days=60)
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
        context["status_cart_link"] = f"/supplier/bookings/?tab=CART{query_params}"
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
        "CART",
    ]:
        tab = Order.Status.PENDING

    if tab.upper() == "CART":
        orders = get_booking_objects(
            request, context["user"], context["seller"], exclude_in_cart=False
        )
    else:
        orders = get_booking_objects(request, context["user"], context["seller"])

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
            "Created By",
            "Service Date",
            "Product",
            "Booking Address",
            "Type",
            "Status",
            "Time Since Order",
            "Supplier Price",
            "Customer Price",
            "Take Rate",
        ]
    else:
        header_row = ["Service Date", "Product", "Booking Address", "Type", "Status"]
    writer.writerow(header_row)
    now_time = timezone.now()
    for order in orders:
        if tab.upper() == "CART" and order.submitted_on is not None:
            continue
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
            row.insert(0, f"{order.order_group}")
            created_by_str = "N/A"
            if order.order_group.created_by:
                created_by_str = order.order_group.created_by.full_name
            row.insert(1, created_by_str)
            if order.submitted_on:
                row.append(humanize.naturaldelta(now_time - order.submitted_on))
            else:
                row.append("Not Submitted")
            row.append("${:,.2f}".format(order.seller_price()))
            row.append("${:,.2f}".format(order.customer_price()))
            row.append(f"{order.take_rate}%")
        writer.writerow(row)
    return response


@login_required(login_url="/admin/login/")
def update_order_status(request, order_id, accept=True, complete=False):
    context = {}
    context["user"] = get_user(request)
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
                orders = get_booking_objects(
                    request, context["user"], context["seller"]
                )
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
def set_intercom_messages_read(request: HttpRequest):
    user = get_user(request)
    # Update User so that Intercom knows they are active.
    IntercomContact.set_last_seen(user.intercom_id)
    return render(request, "supplier_dashboard/snippets/nav_bar_messages_badge.html")


@login_required(login_url="/admin/login/")
def get_intercom_unread_conversations(request: HttpRequest):
    user = get_user(request)
    context = {"user": user}
    # TODO: We could add these to the session/local cache and only remove them when the user clicks on the message.
    # TODO: After order groups go into complete status, mark the conversation as closed.
    # TODO: Wait to update last_seen_at until after they open the chat window
    context["updates"] = IntercomContact.unread_messages(user.intercom_id)
    return render(
        request,
        "supplier_dashboard/snippets/nav_dropdown_messages.html",
        context,
    )


@login_required(login_url="/admin/login/")
def chat(request, order_id=None, conversation_id=None, is_customer=False):
    context = {}
    context["user"] = get_user(request)
    context["seller"] = get_seller(request)
    # Update User so that Intercom knows they are active.
    IntercomContact.set_last_seen(context["user"].intercom_id)
    order = None
    if order_id:
        order = Order.objects.filter(id=order_id).select_related("order_group").first()
        if is_customer:
            chat_url = "supplier_booking_customer_chat"
            conversation_id = order.custmer_intercom_id
        else:
            chat_url = "supplier_booking_chat"
            conversation_id = order.intercom_id
    else:
        if is_customer:
            chat_url = "supplier_customer_chat"
        else:
            chat_url = "supplier_chat"
    context["order"] = order
    if request.method == "POST":
        context["message_form"] = ChatMessageForm(request.POST)
        if context["message_form"].is_valid():
            context["chat"] = IntercomConversation.reply(
                conversation_id,
                context["user"].intercom_id,
                context["message_form"].cleaned_data.get("message"),
            )
            context["message_form"] = ChatMessageForm()
            if order:
                context["get_chat_url"] = reverse(
                    chat_url, kwargs={"order_id": order.id}
                )
            else:
                context["get_chat_url"] = reverse(
                    chat_url, kwargs={"conversation_id": conversation_id}
                )
            if request.headers.get("HX-Request"):
                return render(
                    request,
                    "supplier_dashboard/snippets/chat_messages.html",
                    context,
                )
            else:
                return render(request, "supplier_dashboard/chat.html", context)
        else:
            print("Message form is not valid")
            print(context["message_form"].errors)

    if order:
        # Create a new conversation if one doesn't exist or reply to an existing one with new order information.
        if is_customer:
            if not order.custmer_intercom_id:
                order.create_customer_chat(context["user"].intercom_id)
        else:
            if not order.intercom_id and conversation_id:
                order.create_admin_chat(conversation_id)

    context["chat"] = IntercomConversation.get(
        conversation_id, context["user"].intercom_id
    )
    # Get last message time and check to see if query param last is the same, if it is, then return empty 204.
    context["last_message_time"] = None
    if context["chat"]:
        context["chat"][-1]
        context["last_message_time"] = str(
            context["chat"][-1]["created_at"].timestamp()
        )

    query_params = request.GET.copy()
    query_params["last"] = context["last_message_time"]
    if order:
        context["get_chat_url"] = (
            f"{ reverse(chat_url, kwargs={'order_id': order.id}) }?{query_params.urlencode()}"
        )
    else:
        context["get_chat_url"] = context["get_chat_url"] = (
            f"{ reverse(chat_url, kwargs={'conversation_id': conversation_id}) }?{query_params.urlencode()}"
        )
    if request.headers.get("HX-Request"):
        last_message_ts = request.GET.get("last")
        if last_message_ts and context["last_message_time"]:
            if last_message_ts == context["last_message_time"]:
                return HttpResponse(status=204)
        return render(
            request,
            "supplier_dashboard/snippets/chat_messages.html",
            context,
        )
    else:
        context["message_form"] = ChatMessageForm()
        return render(request, "supplier_dashboard/chat.html", context)


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
        payouts = get_payout_objects(request, context["user"], context["seller"])
        if location_id:
            payouts = payouts.filter(
                order__order_group__seller_product_seller_location__seller_location_id=location_id
            )
        if service_date:
            # filter orders by their payouts created_on date
            payouts = payouts.filter(created_on__date=service_date)
        if request.user.is_staff:
            payouts = payouts.select_related(
                "order__order_group__seller_product_seller_location__seller_location__seller"
            )
            payouts = payouts.order_by(
                # "order__order_group__seller_product_seller_location__seller_location__seller__name",
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
    # service_date = request.GET.get("service_date", None)
    context = {}
    # NOTE: Can add stuff to session if needed to speed up queries.
    context["user"] = get_user(request)
    context["seller"] = get_seller(request)
    orders = get_booking_objects(request, context["user"], context["seller"])

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
    if request.user.is_staff:
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
    if payout.lob_check_id:
        context["is_lob"] = True
        check = payout.get_check()
        if check:
            context["invoice_pdf"] = check.url
            context["thumbnails"] = []
            if check.thumbnails:
                for thumbnail in check.thumbnails:
                    context["thumbnails"].append(thumbnail["large"])
            context["is_pdf"] = True
            context["expected_delivery_date"] = (
                check.expected_delivery_date
            )  # datetime.date
            context["send_date"] = check.send_date  # datetime.datetime
            context["tracking_number"] = check.tracking_number
    # order_line_item = payout.order.order_line_items.all().first()
    # context["is_pdf"] = False
    # if order_line_item:
    #     # TODO: Add support for check once LOB is integrated.
    #     stripe_invoice = order_line_item.get_invoice()
    #     if stripe_invoice:
    #         # hosted_invoice_url
    #         context["hosted_invoice_url"] = stripe_invoice.hosted_invoice_url
    #         context["invoice_pdf"] = stripe_invoice.invoice_pdf
    #         context["is_pdf"] = True
    return render(
        request, "supplier_dashboard/snippets/payout_detail_invoice.html", context
    )


@login_required(login_url="/admin/login/")
def payout_detail(request, payout_id):
    context = {}
    # NOTE: Can add stuff to session if needed to speed up queries.
    context["user"] = get_user(request)
    context["seller"] = get_seller(request)
    payout = Payout.objects.get(id=payout_id)
    if payout.checkbook_payout_id:
        context["related_payouts"] = Payout.objects.filter(
            checkbook_payout_id=payout.checkbook_payout_id
        )
    elif payout.lob_check_id:
        context["related_payouts"] = Payout.objects.filter(
            lob_check_id=payout.lob_check_id
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
    orders = get_booking_objects(request, context["user"], context["seller"])
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
    if request.user.is_staff:
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
        if request.user.is_staff:
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
        seller_locations = get_location_objects(
            request, context["user"], context["seller"]
        )

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
            if is_insurance_compliant and seller_location.is_insurance_expiring_soon:
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
    seller_locations = get_location_objects(request, context["user"], context["seller"])

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
        if is_insurance_compliant and seller_location.is_insurance_expiring_soon:
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
        if seller_location.is_insurance_compliant:
            if seller_location.is_insurance_expiring_soon:
                if (
                    seller_location.gl_coi_expiration_date
                    < seller_location.auto_coi_expiration_date
                    and seller_location.gl_coi_expiration_date
                    < seller_location.workers_comp_coi_expiration_date
                ):
                    insurance_status = f'Expiring Soon | {seller_location.gl_coi_expiration_date.strftime("%Y-%m-%d")} (GL)'
                elif (
                    seller_location.auto_coi_expiration_date
                    < seller_location.gl_coi_expiration_date
                    and seller_location.auto_coi_expiration_date
                    < seller_location.workers_comp_coi_expiration_date
                ):
                    insurance_status = f'Expiring Soon | {seller_location.auto_coi_expiration_date.strftime("%Y-%m-%d")} (Auto)'
                elif (
                    seller_location.workers_comp_coi_expiration_date
                    < seller_location.gl_coi_expiration_date
                    and seller_location.workers_comp_coi_expiration_date
                    < seller_location.auto_coi_expiration_date
                ):
                    insurance_status = f'Expiring Soon | {seller_location.workers_comp_coi_expiration_date.strftime("%Y-%m-%d")} (Workers Comp)'
                else:
                    insurance_status = f'Expiring Soon | {seller_location.workers_comp_coi_expiration_date.strftime("%Y-%m-%d")} (All)'
            else:
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
    user_seller_location_normal = []
    user_seller_location_normal_ids = []
    user_seller_location_admin_users = []
    for user_seller_location in user_seller_locations:
        if user_seller_location.user.type == UserType.ADMIN:
            user_seller_location_admin_users.append(user_seller_location.user.id)
        else:
            user_seller_location_normal.append(user_seller_location)
            user_seller_location_normal_ids.append(user_seller_location.user.id)

    context["user_seller_locations"] = user_seller_location_normal

    # Get the list of UserGroup Users that are not already associated with the SellerLocation.
    seller = SellerLocation.objects.get(id=location_id).seller

    if UserGroup.objects.filter(seller=seller).exists():
        user_group = UserGroup.objects.get(seller=seller)

        context["non_associated_users"] = (
            User.objects.filter(user_group_id=user_group.id)
            .exclude(
                id__in=user_seller_location_normal_ids,
            )
            .exclude(
                type=UserType.ADMIN,
            )
        )

        # Get ADMIN users for this UserGroup.
        admin_users = User.objects.filter(
            user_group_id=user_group.id,
            type=UserType.ADMIN,
        )
        context["location_admins"] = []
        for user in admin_users:
            if user.id in user_seller_location_admin_users:
                context["location_admins"].append({"user": user, "notify": True})
            else:
                context["location_admins"].append({"user": user, "notify": False})

    return render(request, "supplier_dashboard/location_detail.html", context)


@login_required(login_url="/admin/login/")
def seller_location_user_add(request, seller_location_id, user_id):

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
        if request.headers.get("HX-Request"):
            return render(
                request,
                "supplier_dashboard/snippets/seller_location_user_row.html",
                {
                    "location_admin": {"user": user, "notify": True},
                    "seller_location": seller_location,
                },
            )
        else:
            return redirect(
                reverse(
                    "supplier_location_detail",
                    kwargs={
                        "location_id": seller_location_id,
                    },
                )
            )


@login_required(login_url="/admin/login/")
def seller_location_user_remove(request, seller_location_id, user_id):

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
        if request.headers.get("HX-Request"):
            return render(
                request,
                "supplier_dashboard/snippets/seller_location_user_row.html",
                {
                    "location_admin": {"user": user, "notify": False},
                    "seller_location": seller_location,
                },
            )
        else:
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
    invoices = get_recieved_invoice_objects(request, context["user"], context["seller"])

    if service_date:
        invoices = invoices.filter(invoice_date=service_date)

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


def parse_order_id(s):
    start = s.rfind("[") + 1
    end = s.find("]", start)
    if start > 0 and end > 0:
        return s[start:end]
    else:
        return None


@api_view(["POST"])
@authentication_classes([])
@permission_classes([])
def intercom_new_conversation_webhook(request):
    whitelisted_ips = [
        "34.231.68.152",
        "34.197.76.213",
        "35.171.78.91",
        "35.169.138.21",
        "52.70.27.159",
        "52.44.63.161",
    ]
    # Extract ip from 'HTTP_X_FORWARDED_FOR': '34.197.76.213,34.197.76.213,172.70.174.238', or 'HTTP_DO_CONNECTING_IP': '34.197.76.213'
    if request.META.get("HTTP_DO_CONNECTING_IP") not in whitelisted_ips:
        logger.warning(
            f"intercom_new_conversation_webhook:INVALID IP: data:[{request.data}]-META:[{request.META}]"
        )
        # return Response({"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)
    try:
        find_str = "🚀 Yippee! New"
        conversation_id = request.data.get("data", {}).get("item", {}).get("id")
        subject = (
            request.data.get("data", {})
            .get("item", {})
            .get("source", {})
            .get("subject", "")
        )
        if find_str in subject:
            order_id = parse_order_id(subject)
            if order_id:
                logger.info(
                    f"intercom_new_conversation_webhook: subject:[{subject}]-order_id:[{order_id}]-conversation_id:[{conversation_id}]"
                )
                order = Order.objects.get(id=order_id)
                order.create_admin_chat(conversation_id)
            else:
                logger.error(
                    f"intercom_new_conversation_webhook: Order ID not found in subject[{subject}]"
                )
    except Order.DoesNotExist as e:
        logger.error(
            f"intercom_new_conversation_webhook: Order not found for order_id[{order_id}]",
            exc_info=e,
        )
    except Exception as e:
        logger.error(
            f"intercom_new_conversation_webhook: [{e}]-data[{request.data}]", exc_info=e
        )
        return Response("error", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return Response("OK", status=status.HTTP_200_OK)
