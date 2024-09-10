import ast
import datetime
import json
import logging
import uuid
from decimal import Decimal
from functools import wraps
from typing import List, Union
from urllib.parse import urlencode

import requests
import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.core.validators import validate_email
from django.db import IntegrityError
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.response import Response

from admin_approvals.models import UserGroupAdminApprovalUserInvite
from api.models import (
    AddOn,
    MainProduct,
    MainProductAddOn,
    MainProductCategory,
    MainProductCategoryInfo,
    MainProductInfo,
    MainProductServiceRecurringFrequency,
    MainProductWasteType,
    Order,
    OrderGroup,
    OrderGroupMaterial,
    OrderLineItemType,
    Product,
    ProductAddOnChoice,
    SellerLocation,
    SellerProduct,
    SellerProductSellerLocation,
    ServiceRecurringFrequency,
    Subscription,
    TimeSlot,
    User,
    UserAddress,
    UserAddressType,
    UserGroup,
)
from api.models.seller.seller_product_seller_location_material_waste_type import (
    SellerProductSellerLocationMaterialWasteType,
)
from api.models.user.user import CompanyUtils as UserUtils
from api.models.user.user_address import CompanyUtils as UserAddressUtils
from api.models.user.user_group import CompanyUtils as UserGroupUtils
from api.models.user.user_user_address import UserUserAddress
from api.models.waste_type import WasteType
from billing.models import Invoice
from common.models.choices.user_type import UserType
from communications.intercom.utils.utils import get_json_safe_value
from matching_engine.matching_engine import MatchingEngine
from matching_engine.utils.prep_seller_product_seller_locations_for_response import (
    prep_seller_product_seller_locations_for_response,
)
from payment_methods.models import PaymentMethod
from pricing_engine.api.v1.serializers.response.pricing_engine_response import (
    PricingEngineResponseSerializer,
)
from pricing_engine.pricing_engine import PricingEngine
from cart.models import CheckoutOrder
from cart.utils import QuoteUtils

from .forms import (
    AccessDetailsForm,
    OrderGroupForm,
    OrderGroupSwapForm,
    PlacementDetailsForm,
    UserAddressForm,
    UserForm,
    UserGroupForm,
    UserInviteForm,
)

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY


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


class DecimalEncoder(json.JSONEncoder):
    """Encode Decimal objects to string."""

    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)


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
    return request.session.get("customer_user_id") and request.session.get(
        "customer_user_id"
    ) != str(request.user.id)


def get_user_group(request: HttpRequest) -> Union[UserGroup, None]:
    """Returns the current UserGroup. This handles the case where the user is impersonating another user.
    If the user is impersonating, it will return the UserGroup of the impersonated user.
    The the user is staff and is not impersonating a user, then it will return None.

    Args:
        request (HttpRequest): Current request object.

    Returns:
        [UserGroup, None]: Returns the UserGroup object or None. None means staff user.
    """

    if is_impersonating(request) and request.session["customer_user_group_id"]:
        user_group = UserGroup.objects.get(id=request.session["customer_user_group_id"])
    elif request.user.is_staff:
        user_group = None
    else:
        # Normal user
        if request.session.get("customer_user_group_id"):
            user_group = UserGroup.objects.get(
                id=request.session["customer_user_group_id"]
            )
        else:
            # Cache user_group id for faster lookups
            user_group = request.user.user_group
            request.session["customer_user_group_id"] = get_json_safe_value(
                user_group.id
            )

    return user_group


def get_user(request: HttpRequest) -> User:
    """Returns the current user. This handles the case where the user is impersonating another user.

    Args:
        request (HttpRequest): Current request object.

    Returns:
        dict: Dictionary of the User object.
    """
    if is_impersonating(request):
        user = User.objects.get(id=request.session.get("customer_user_id"))
    else:
        user = request.user
    return user


def get_user_group_user_objects(
    request: HttpRequest, user: User, user_group: UserGroup, search_q: str = None
):
    """Returns the users for the current UserGroup.

    If user is:
        - staff, then all users are returned.
        - not staff
            - is admin, then return all users for the UserGroup.
            - not admin, then only users in the logged in user's user group.

    Args:
        request (HttpRequest): Request object from the view.
        user (User): User object.
        user_group (UserGroup): UserGroup object. NOTE: May be None.

    Returns:
        QuerySet[User]: The users queryset.
    """
    if not user.is_staff and user.type != UserType.ADMIN:
        users = User.objects.filter(user_group_id=user.user_group_id)
    else:
        if request.user.is_staff and not is_impersonating(request):
            # Global View: Get all users.
            users = User.objects.all()
        elif user_group:
            users = User.objects.filter(user_group_id=user_group.id)
        else:
            # Individual user.
            users = User.objects.filter(id=user.id)
    if search_q:
        users = users.filter(
            Q(first_name__icontains=search_q)
            | Q(last_name__icontains=search_q)
            | Q(email__icontains=search_q)
        )
    return users


def get_booking_objects(
    request: HttpRequest, user: User, user_group: UserGroup, exclude_in_cart=True
):
    """Returns the orders for the current UserGroup.

    If user is:
        - staff, then all orders for all of UserGroups are returned.
        - not staff
            - is admin, then return all orders for the UserGroup.
            - not admin, then only orders for the UserGroup locations the user is associated with are returned.

    Args:
        request (HttpRequest): Request object from the view.
        user (User): User object.
        user_group (UserGroup): UserGroup object. NOTE: May be None.

    Returns:
        QuerySet[Order]: The orders queryset.
    """
    if not user.is_staff and user.type != UserType.ADMIN:
        user_user_location_ids = (
            UserUserAddress.objects.filter(user_id=user.id)
            .select_related("user_address")
            .values_list("user_address_id", flat=True)
        )
        orders = Order.objects.filter(
            order_group__user_address__in=user_user_location_ids
        )
    else:
        if request.user.is_staff and not is_impersonating(request):
            # Global View: Get all orders.
            orders = Order.objects.all()
        elif user_group:
            orders = Order.objects.filter(
                order_group__user__user_group_id=user_group.id
            )
        else:
            # Individual user. Get all orders for the user.
            orders = Order.objects.filter(order_group__user_id=user.id)
    if exclude_in_cart:
        orders = orders.filter(submitted_on__isnull=False)
    return orders


def get_order_group_objects(request: HttpRequest, user: User, user_group: UserGroup):
    """Returns the order_groups for the current UserGroup.

    If user is:
        - staff, then all order_groups for all of UserGroups are returned.
        - not staff
            - is admin, then return all order_groups for the UserGroup.
            - not admin, then only order_groups for the UserGroup locations the user is associated with are returned.

    Args:
        request (HttpRequest): Request object from the view.
        user (User): User object.
        user_group (UserGroup): UserGroup object. NOTE: May be None.

    Returns:
        QuerySet[OrderGroup]: The order_groups queryset.
    """
    if not user.is_staff and user.type != UserType.ADMIN:
        user_user_location_ids = (
            UserUserAddress.objects.filter(user_id=user.id)
            .select_related("user_address")
            .values_list("user_address_id", flat=True)
        )
        order_groups = OrderGroup.objects.filter(
            user_address__in=user_user_location_ids
        )
    else:
        if request.user.is_staff and not is_impersonating(request):
            # Global View: Get all order_groups.
            order_groups = OrderGroup.objects.all()
        elif user_group:
            order_groups = OrderGroup.objects.filter(user__user_group_id=user_group.id)
        else:
            # Individual user. Get all orders for the user.
            order_groups = OrderGroup.objects.filter(user_id=user.id)
    return order_groups


def get_location_objects(
    request: HttpRequest, user: User, user_group: UserGroup, search_q: str = None
):
    """Returns the locations for the current UserGroup.

    If user is:
        - staff, then all locations for all of UserGroups are returned.
        - not staff
            - is admin, then return all locations for the UserGroup.
            - not admin, then only locations for the UserGroup locations the user is associated with are returned.

    Args:
        request (HttpRequest): Request object from the view.
        user (User): User object.
        user_group (UserGroup): UserGroup object. NOTE: May be None.
        search_q (str): [Optional] Search query string.

    Returns:
        QuerySet[Location]: The locations queryset.
    """
    if not user.is_staff and user.type != UserType.ADMIN:
        user_user_locations = UserUserAddress.objects.filter(
            user_id=user.id
        ).select_related("user_address")
        if search_q:
            user_user_locations = user_user_locations.filter(
                Q(user_address__name__icontains=search_q)
                | Q(user_address__street__icontains=search_q)
                | Q(user_address__city__icontains=search_q)
                | Q(user_address__state__icontains=search_q)
                | Q(user_address__postal_code__icontains=search_q)
            )
        user_user_locations = user_user_locations.order_by("-user_address__created_on")
        locations = [
            user_user_location.user_address
            for user_user_location in user_user_locations
        ]
    else:
        if request.user.is_staff and not is_impersonating(request):
            # Global View: Get all locations.
            locations = UserAddress.objects.all()
            locations = locations.order_by("name", "-created_on")
        elif user_group:
            locations = UserAddress.objects.filter(user_group_id=user_group.id)
            locations = locations.order_by("-created_on")
        else:
            # Individual user. Get all locations for the user.
            locations = UserAddress.objects.filter(user_id=user.id)
            locations = locations.order_by("-created_on")
        if search_q:
            locations = locations.filter(
                Q(name__icontains=search_q)
                | Q(street__icontains=search_q)
                | Q(city__icontains=search_q)
                | Q(state__icontains=search_q)
                | Q(postal_code__icontains=search_q)
            )
    return locations


def get_invoice_objects(request: HttpRequest, user: User, user_group: UserGroup):
    """Returns the invoices for the current user_group.

    If user is:
        - staff, then all invoices for all of user_groups are returned.
        - not staff
            - is admin, then return all invoices for the user_group.
            - not admin, then only invoices for the user_group locations the user is associated with are returned.

    Args:
        request (HttpRequest): Request object from the view.
        user (User): User object.
        user_group (UserGroup): UserGroup object. NOTE: May be None.

    Returns:
        QuerySet[Invoice]: The invoices queryset.
    """

    if not user.is_staff and user.type != UserType.ADMIN:
        user_user_location_ids = (
            UserUserAddress.objects.filter(user_id=user.id)
            .select_related("user_address")
            .values_list("user_address_id", flat=True)
        )
        invoices = Invoice.objects.filter(user_address__in=user_user_location_ids)
    else:
        if request.user.is_staff and not is_impersonating(request):
            # Global View: Get all invoices.
            invoices = Invoice.objects.all()
        elif user_group:
            invoices = Invoice.objects.filter(
                user_address__user__user_group_id=user_group.id
            )
        else:
            # Individual user. Get all invoices for the user.
            invoices = Invoice.objects.filter(user_address__user_id=user.id)
    return invoices


########################
# Page views
########################
def catch_errors(redirect_url_name=None):
    """
    Decorator for views that enclose the view in a try/except block.
    If the test_func raises an exception, the decorator will catch it and
    attach a messages.error to the request object.
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapper_view(request, *args, **kwargs):
            try:
                return view_func(request, *args, **kwargs)
            except Exception as e:
                error_message = f"An unhandled error [{e}] occurred while accessing view [{str(view_func.__name__)}] on path [{request.get_full_path()}]"
                logger.error(
                    f"catch_errors: view: {str(view_func.__name__)} path:{request.get_full_path()}",
                    exc_info=e,
                )
                if request.headers.get("HX-Request"):
                    # Reraise htmx errors since those don't cause a 500 error.
                    raise
                # Add a _is_redirect flag to the redirect url to avoid infinite loops.
                query_params = request.GET.copy()
                _is_redirect = query_params.get("_is_redirect", None)
                if _is_redirect == "1" or _is_redirect == 1:
                    return render(
                        request,
                        "customer_dashboard/error.html",
                        {"error_message": error_message},
                    )
                messages.error(request, f"A server error occurred: {e}")
                query_params["_is_redirect"] = 1
                if redirect_url_name:
                    query_params.urlencode()
                    return HttpResponseRedirect(
                        f"{reverse(redirect_url_name)}?{query_params.urlencode()}"
                    )
                else:
                    full_path = f"{request.path}?{query_params.urlencode()}"
                    return HttpResponseRedirect(full_path)

        return _wrapper_view

    return decorator


# Add redirect to auth0 login if not logged in.
def customer_logout(request):
    logout(request)
    # Redirect to a success page.
    return HttpResponseRedirect("https://trydownstream.com/")


@login_required(login_url="/admin/login/")
def customer_search(request, is_selection=False):
    context = {}
    if request.method == "POST":
        search = request.POST.get("search")
        search = search.strip()
        if not search:
            return HttpResponse(status=204)
        try:
            search_id = uuid.UUID(search)
            user_groups = UserGroup.objects.filter(id=search_id)
            users = User.objects.filter(id=search_id)
        except ValueError:
            isearch = search.casefold()
            user_groups = UserGroup.objects.filter(name__icontains=isearch)
            users = User.objects.filter(
                Q(first_name__icontains=isearch)
                | Q(last_name__icontains=isearch)
                | Q(email__icontains=isearch)
            )
        context["user_groups"] = user_groups
        context["users"] = users

    if is_selection:
        return render(
            request,
            "customer_dashboard/snippets/user_group_search_selection.html",
            context,
        )
    else:
        return render(
            request, "customer_dashboard/snippets/user_search_list.html", context
        )


@login_required(login_url="/admin/login/")
def customer_impersonation_start(request):
    if request.user.is_staff:
        redirect_url = reverse("customer_home")
        if request.method == "POST":
            user_group_id = request.POST.get("user_group_id")
            user_id = request.POST.get("user_id")
            if request.POST.get("redirect_url"):
                redirect_url = request.GET.get("redirect_url")
        elif request.method == "GET":
            user_group_id = request.GET.get("user_group_id")
            user_id = request.GET.get("user_id")
            if request.GET.get("redirect_url"):
                redirect_url = request.GET.get("redirect_url")
        else:
            return HttpResponse("Not Implemented", status=406)
        try:
            user = None
            if user_group_id:
                user_group = UserGroup.objects.get(id=user_group_id)
                user = user_group.users.filter(type=UserType.ADMIN).first()
            elif user_id:
                user = User.objects.get(id=user_id)
                # user_group = user.user_group
                # if user_group:
                #     user_group_id = user_group.id
            if not user:
                user = user_group.users.first()
                if not user:
                    raise User.DoesNotExist
                messages.warning(
                    request,
                    "No admin user found for UserGroup. UserGroup should have at least one admin user.",
                )
            if not user:
                raise User.DoesNotExist
            request.session["customer_user_group_id"] = get_json_safe_value(
                user_group_id
            )
            request.session["customer_user_id"] = get_json_safe_value(user.id)
            return HttpResponseRedirect(redirect_url)
        except User.DoesNotExist:
            messages.error(
                request,
                "No admin user found for UserGroup. UserGroup must have at least one admin user.",
            )
            return HttpResponseRedirect("/customer/")
        except Exception:
            return HttpResponse("Not Found", status=404)
    else:
        return HttpResponse("Unauthorized", status=401)


@login_required(login_url="/admin/login/")
def customer_impersonation_stop(request):
    if request.session.get("customer_user_id"):
        del request.session["customer_user_id"]
    if request.session.get("customer_user_group_id"):
        del request.session["customer_user_group_id"]
    return HttpResponseRedirect("/customer/")


def get_user_context(request: HttpRequest, add_user_group=True):
    """Returns the common context data for the views."""
    context = {}
    context["BASIS_THEORY_API_KEY"] = settings.BASIS_THEORY_PUB_API_KEY
    context["user"] = get_user(request)
    context["is_impersonating"] = is_impersonating(request)
    if add_user_group:
        context["user_group"] = get_user_group(request)
    return context


@login_required(login_url="/admin/login/")
@catch_errors()
def index(request):
    context = get_user_context(request)
    if request.headers.get("HX-Request"):
        orders = get_booking_objects(request, context["user"], context["user_group"])
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
            context["earnings"] += float(order.customer_price())
            if order.end_date >= one_year_ago:
                earnings_by_month[order.end_date.month - 1] += float(
                    order.customer_price()
                )

            category = (
                order.order_group.seller_product_seller_location.seller_product.product.main_product.main_product_category.name
            )
            if category not in earnings_by_category:
                earnings_by_category[category] = {"amount": 0, "percent": 0}
            earnings_by_category[category]["amount"] += float(order.customer_price())

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
        # context["pending_count"] = orders.count()
        locations = get_location_objects(
            request, context["user"], context["user_group"]
        )
        if isinstance(locations, list):
            context["location_count"] = len(locations)
        else:
            context["location_count"] = locations.count()
        location_users = get_user_group_user_objects(
            request, context["user"], context["user_group"]
        )
        context["user_count"] = location_users.count()
        context["chart_data"] = get_dashboard_chart_data(earnings_by_month)
        # context["chart_data"] = json.dumps(get_dashboard_chart_data(earnings_by_month))

        return render(request, "customer_dashboard/snippets/dashboard.html", context)
    else:
        return render(request, "customer_dashboard/index.html", context)


@login_required(login_url="/admin/login/")
@catch_errors()
def new_order(request):
    context = get_user_context(request)
    main_product_categories = MainProductCategory.objects.all().order_by("sort")
    context["main_product_categories"] = main_product_categories

    return render(
        request, "customer_dashboard/new_order/main_product_categories.html", context
    )


@login_required(login_url="/admin/login/")
def new_order_category_price(request, category_id):
    context = {}
    # NOTE: Causes a lot of heavy db queries. Need to optimize.
    main_product_category = MainProductCategory.objects.get(id=category_id)
    context["price_from"] = main_product_category.price_from
    # Assume htmx request
    # if request.headers.get("HX-Request"):
    return render(
        request, "customer_dashboard/snippets/category_price_from.html", context
    )


@login_required(login_url="/admin/login/")
def user_address_search(request):
    context = {}
    if request.method == "POST":
        search = request.POST.get("q")
        search = search.strip()
        if not search:
            return HttpResponse(status=204)
        try:
            user_address_id = uuid.UUID(search)
            user_addresses = UserAddress.objects.filter(id=user_address_id)
        except ValueError:
            user_addresses = UserAddress.objects.filter(
                Q(name__icontains=search)
                | Q(street__icontains=search)
                | Q(city__icontains=search)
                | Q(state__icontains=search)
                | Q(postal_code__icontains=search)
            )
        context["user_addresses"] = user_addresses

    return render(
        request,
        "customer_dashboard/snippets/user_address_search_selection.html",
        context,
    )


@login_required(login_url="/admin/login/")
@catch_errors()
def new_order_2(request, category_id):
    context = get_user_context(request)
    main_product_category = MainProductCategory.objects.filter(id=category_id)
    main_product_category = main_product_category.prefetch_related("main_products")
    main_product_category = main_product_category.first()
    main_products = main_product_category.main_products.all().order_by("sort")
    context["main_product_category"] = main_product_category
    context["main_products"] = []
    for main_product in main_products:
        main_product_dict = {}
        main_product_dict["product"] = main_product
        main_product_dict["infos"] = main_product.mainproductinfo_set.all().order_by(
            "sort"
        )
        context["main_products"].append(main_product_dict)

    return render(request, "customer_dashboard/new_order/main_products.html", context)


@login_required(login_url="/admin/login/")
@catch_errors()
def new_order_3(request, product_id):
    context = get_user_context(request)
    context["product_id"] = product_id
    # TODO: Add a button that allows adding an address.
    # The button could open a modal that allows adding an address.
    main_product = MainProduct.objects.filter(id=product_id)
    main_product = main_product.select_related("main_product_category")
    main_product = main_product.first()
    context["main_product"] = main_product
    product_waste_types = MainProductWasteType.objects.filter(
        main_product_id=main_product.id
    )
    product_waste_types = product_waste_types.select_related("waste_type")
    context["product_waste_types"] = product_waste_types
    add_ons = AddOn.objects.filter(main_product_id=product_id)
    # Get addon choices for each add_on and display the choices under the add_on.
    context["product_add_ons"] = []
    for add_on in add_ons:
        context["product_add_ons"].append(
            {"add_on": add_on, "choices": add_on.choices.all()}
        )
    context["user_addresses"] = get_location_objects(
        request, context["user"], context["user_group"]
    )
    if request.method == "POST":
        user_address_id = request.POST.get("user_address")
        if user_address_id:
            context["selected_user_address"] = UserAddress.objects.get(
                id=user_address_id
            )
        query_params = {
            "product_id": context["product_id"],
            "user_address": request.POST.get("user_address"),
            "delivery_date": request.POST.get("delivery_date"),
            "removal_date": request.POST.get("removal_date"),
            "schedule_window": request.POST.get("schedule_window"),
            "product_add_on_choices": request.POST.getlist("product_add_on_choices"),
            "product_waste_types": request.POST.getlist("product_waste_types"),
        }
        if request.POST.get("times_per_week"):
            query_params["times_per_week"] = request.POST.get("times_per_week")
        if request.POST.get("shift_count"):
            query_params["shift_count"] = request.POST.get("shift_count")
        if not query_params["removal_date"]:
            # This happens for one-time orders like junk removal,
            # where the removal date is the same as the delivery date.
            query_params["removal_date"] = query_params["delivery_date"]
        try:
            form = OrderGroupForm(
                request.POST,
                request.FILES,
                user_addresses=context["user_addresses"],
                main_product=context["main_product"],
                product_waste_types=context["product_waste_types"],
                product_add_ons=context["product_add_ons"],
            )
            context["form"] = form
            # Use Django form validation to validate the form.
            # If not valid, then display error message.
            # If valid, then redirect to next page.
            if form.is_valid():
                pass
            else:
                raise InvalidFormError(form, "Invalid OrderGroupForm")
            return HttpResponseRedirect(
                f"{reverse('customer_new_order_4')}?{urlencode(query_params, doseq=True)}"
            )
        except InvalidFormError as e:
            # This will let bootstrap know to highlight the fields with errors.
            for field in e.form.errors:
                if e.form.fields[field].widget.attrs.get("class", None) is None:
                    e.form.fields[field].widget.attrs["class"] = "is-invalid"
                else:
                    e.form.fields[field].widget.attrs["class"] += " is-invalid"
        except Exception as e:
            messages.error(
                request, f"Error saving, please contact us if this continues: [{e}]."
            )
    else:
        context["form"] = OrderGroupForm(
            user_addresses=context["user_addresses"],
            main_product=context["main_product"],
            product_waste_types=context["product_waste_types"],
            product_add_ons=context["product_add_ons"],
        )

    return render(
        request, "customer_dashboard/new_order/main_product_detail.html", context
    )


@login_required(login_url="/admin/login/")
@catch_errors()
def new_order_4(request):
    # import time
    # start_time = time.time()
    context = get_user_context(request)
    context["product_id"] = request.GET.get("product_id")
    context["user_address"] = request.GET.get("user_address")
    context["product_waste_types"] = request.GET.getlist("product_waste_types")
    if context["product_waste_types"] and context["product_waste_types"][0] == "":
        context["product_waste_types"] = []
    context["product_add_on_choices"] = request.GET.getlist("product_add_on_choices")
    if context["product_add_on_choices"] and context["product_add_on_choices"][0] == "":
        context["product_add_on_choices"] = []
    context["schedule_window"] = request.GET.get("schedule_window", "")
    context["times_per_week"] = request.GET.get("times_per_week", "")
    if context["times_per_week"]:
        context["times_per_week"] = int(context["times_per_week"])
    context["delivery_date"] = request.GET.get("delivery_date")
    context["removal_date"] = request.GET.get("removal_date", "")
    # step_time = time.time()
    # print(f"Extract parameters: {step_time - start_time}")
    # if product_waste_types:
    waste_type = None
    waste_type_id = None
    # TODO: We are only using the first waste type for now.
    if context["product_waste_types"]:
        main_product_waste_type = MainProductWasteType.objects.filter(
            id=context["product_waste_types"][0]
        ).first()
        waste_type = main_product_waste_type.waste_type
        waste_type_id = waste_type.id
    if waste_type_id:
        context["waste_type"] = waste_type_id

    products = Product.objects.filter(main_product_id=context["product_id"])
    # Find the products that have the waste types and add ons.
    if context["product_add_on_choices"]:
        prod_addon_choice_set = set(context["product_add_on_choices"])
        for product in products:
            product_addon_choices_db = ProductAddOnChoice.objects.filter(
                product_id=product.id
            ).values_list("add_on_choice_id", flat=True)
            db_choices = set([str(choice) for choice in product_addon_choices_db])
            if db_choices == prod_addon_choice_set:
                context["product"] = product
                break
    elif products.count() == 1:
        context["product"] = products.first()
    elif products.count() > 1:
        messages.error(
            request,
            "Multiple products found. Only one product of each type should exist. You might encounter errors.",
        )
        context["product"] = products.first()
    if context.get("product", None) is None:
        messages.error(request, "Product not found.")
        return HttpResponseRedirect(reverse("customer_new_order"))

    # step_time = time.time()
    # print(f"Find Product: {step_time - start_time}")
    # We know the product the user wants, so now find the seller locations that offer the product.
    user_address_obj = UserAddress.objects.filter(id=context["user_address"]).first()
    seller_product_seller_locations = (
        MatchingEngine.get_possible_seller_product_seller_locations(
            context["product"],
            user_address_obj,
            waste_type,
        )
    )
    # print("Seller Product Seller Locations")
    # print(seller_product_seller_locations)
    # step_time = time.time()
    # print(f"Find Seller Locations: {step_time - start_time}")

    # if request.method == "POST":
    # start_date = datetime.datetime.strptime(context["delivery_date"], "%Y-%m-%d")
    # end_date = None
    # if context["removal_date"]:
    #     end_date = datetime.datetime.strptime(context["removal_date"], "%Y-%m-%d")
    context["seller_product_seller_locations"] = []
    context["max_discount_100"] = round(
        float(context["product"].main_product.max_discount) * 100, 1
    )

    for seller_product_seller_location in seller_product_seller_locations:
        seller_d = {}
        seller_d["seller_product_seller_location"] = seller_product_seller_location
        pricing = PricingEngine.get_price(
            user_address=UserAddress.objects.get(
                id=context["user_address"],
            ),
            seller_product_seller_location=seller_product_seller_location,
            start_date=datetime.datetime.strptime(context["delivery_date"], "%Y-%m-%d"),
            end_date=datetime.datetime.strptime(context["delivery_date"], "%Y-%m-%d"),
            waste_type=(
                WasteType.objects.get(id=waste_type_id) if waste_type_id else None
            ),
            times_per_week=(
                context["times_per_week"] if context["times_per_week"] else None
            ),
            shift_count=context.get("shift_count", None),
        )

        seller_d["price_data"] = PricingEngineResponseSerializer(pricing).data

        # Update the SellerProductSellerLocation to default to the take rate.
        seller_d["seller_product_seller_location"] = (
            prep_seller_product_seller_locations_for_response(
                main_product=context["product"].main_product,
                seller_product_seller_locations=[seller_product_seller_location],
            )[0]
        )
        # Include because SellerProductSellerLocationSerializer does not include waste types info needed
        # needed for price_details_modal.
        seller_d["spsl"] = seller_product_seller_location

        context["seller_product_seller_locations"].append(seller_d)

    # step_time = time.time()
    # print(f"Get Prices: {step_time - start_time}")
    # context["seller_locations"] = seller_product_location.first().seller_location
    return render(
        request,
        "customer_dashboard/new_order/main_product_detail_pricing.html",
        context,
    )


@login_required(login_url="/admin/login/")
@catch_errors()
def new_order_5(request):
    context = get_user_context(request)
    context["cart"] = {}
    if request.method == "POST":
        # Create the order group and orders.
        seller_product_seller_location_id = request.POST.get(
            "seller_product_seller_location_id"
        )
        discount = request.POST.get("discount")
        product_id = request.POST.get("product_id")
        user_address_id = request.POST.get("user_address")
        product_waste_types = request.POST.get("product_waste_types")
        if product_waste_types:
            product_waste_types = ast.literal_eval(product_waste_types)
        waste_type_id = request.POST.get("waste_type")
        placement_details = request.POST.get("placement_details")
        # product_add_on_choices = request.POST.get("product_add_on_choices")
        schedule_window = request.POST.get("schedule_window", "Morning (7am-11am)")
        times_per_week = (
            int(request.POST.get("times_per_week"))
            if request.POST.get("times_per_week")
            else None
        )
        delivery_date = datetime.datetime.strptime(
            request.POST.get("delivery_date"),
            "%Y-%m-%d",
        )

        # removal_date = request.POST.get("removal_date")
        main_product = MainProduct.objects.filter(id=product_id)
        main_product = main_product.select_related("main_product_category")
        # main_product = main_product.prefetch_related("products")
        main_product = main_product.first()

        # Set the discount. If no discount is set, then default to 0.
        discount = float(discount) if discount else 0
        print("Discount: ", discount)

        context["main_product"] = main_product
        seller_product_location = SellerProductSellerLocation.objects.get(
            id=seller_product_seller_location_id
        )
        user_address = UserAddress.objects.filter(id=user_address_id).first()
        if main_product.has_material and hasattr(seller_product_location, "material"):
            material_waste_type = (
                SellerProductSellerLocationMaterialWasteType.objects.filter(
                    seller_product_seller_location_material=seller_product_location.material
                )
                .filter(main_product_waste_type__waste_type_id=waste_type_id)
                .first()
            )
            if not material_waste_type:
                messages.error(
                    request,
                    "Material waste type not found. Please contact us if this continues.",
                )
                return HttpResponseRedirect(reverse("customer_new_order"))

        # Get the default take rate and calculate the take rate based on the discount.
        default_take_rate_percent = float(main_product.default_take_rate) / 100
        default_price_multiplier = 1 + default_take_rate_percent
        discount_percent = discount / 100
        price_with_discount = default_price_multiplier * (1 - discount_percent)
        take_rate = price_with_discount - 1

        # Create order group and orders
        order_group = OrderGroup(
            user=context["user"],
            user_address=user_address,
            seller_product_seller_location_id=seller_product_seller_location_id,
            start_date=delivery_date,
            take_rate=take_rate * 100,
        )
        if times_per_week:
            order_group.times_per_week = times_per_week
        if waste_type_id:
            order_group.waste_type_id = waste_type_id
        # NOTE: Commenting removal_date out for now. We may, possibly, maybe add this back in later.
        # This means that we never set the removal date on the OrderGroup when creating it.
        # if removal_date:
        #     order_group.end_date = removal_date
        if seller_product_location.delivery_fee:
            order_group.delivery_fee = seller_product_location.delivery_fee
        if seller_product_location.removal_fee:
            order_group.removal_fee = seller_product_location.removal_fee
        if schedule_window:
            time_slot_name = schedule_window.split(" ")[0]
            time_slot = TimeSlot.objects.filter(name=time_slot_name).first()
            if time_slot:
                order_group.time_slot = time_slot
        order_group.save()

        # Create the order (Let submitted on null, this indicates that the order is in the cart)
        # The first order of an order group always gets the same start and end date.
        order = order_group.create_delivery(
            delivery_date, schedule_window=schedule_window
        )
        # context["cart"][order_group.id] = {
        #     "order_group": order_group,
        #     "price": order.customer_price()
        # }
    elif request.method == "DELETE":
        # Delete the order group and orders.
        order_group_id = request.GET.get("id")
        order_id = request.GET.get("order_id")
        subtotal = request.GET.get("subtotal")
        cart_count = request.GET.get("count")
        customer_price = request.GET.get("price")
        groupcount = request.GET.get("groupcount")
        order_group = OrderGroup.objects.filter(id=order_group_id).first()
        if customer_price:
            customer_price = float(customer_price)
        else:
            customer_price = 0
        # Only delete the single order/transaction, not the entire order group, except if it is the first order.
        order = Order.objects.filter(id=order_id).first()
        if order_group:
            order_group_orders = order_group.orders.all()
            is_first_order = (
                order.order_group.start_date == order.start_date
                and order_group_orders.count() == 1
            )
            if is_first_order:
                # A single transaction Order, which is a delivery or one-time service.
                # Delete any related protected objects, like orders and subscriptions.
                sub_obj = Subscription.objects.filter(
                    order_group_id=order_group.id
                ).first()
                if sub_obj:
                    sub_obj.delete()
                for ordr in order_group.orders.all():
                    # del_subtotal += order.customer_price()
                    ordr.delete()
                order_group.delete()
            elif order:
                order.delete()
            context["user_address"] = order_group.user_address_id
        if subtotal:
            context["subtotal"] = float(subtotal) - float(customer_price)
        if cart_count:
            context["cart_count"] = int(cart_count) - 1
        if groupcount:
            context["groupcount"] = int(groupcount) - 1
        if order_group:
            messages.success(request, "Order removed from cart.")
        else:
            messages.error(request, f"Order not found [{order_group_id}].")
        if request.headers.get("HX-Request"):
            return render(
                request,
                "customer_dashboard/new_order/cart_remove_item.html",
                context,
            )

    query_params = request.GET.copy()
    # Load the cart page
    context["subtotal"] = 0
    context["cart_count"] = 0

    # This is an HTMX request, so respond with html snippet
    if request.headers.get("HX-Request"):
        filter_qry = request.GET.get("filter")
        my_carts = request.GET.get("my_carts")
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        if start_date:
            # Parse date object
            start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
            check_date = start_date
        else:
            check_date = timezone.now().date()

        if end_date:
            end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()

        # Pull all orders with submitted_on = None and show them in the cart.
        orders = get_booking_objects(
            request, context["user"], context["user_group"], exclude_in_cart=False
        )
        orders = orders.filter(submitted_on__isnull=True)

        if my_carts:
            context["help_text"] = "My "
            orders = orders.filter(order_group__user_id=context["user"].id)
        else:
            context["help_text"] = "All "

        if filter_qry == "new":
            # Displays all open orders that the Order.CreatedDate == today
            if start_date and end_date:
                # Could use https://docs.djangoproject.com/en/5.0/ref/models/querysets/#range
                orders = orders.filter(
                    Q(created_on__date__gte=start_date)
                    & Q(created_on__date__lte=end_date)
                )
                context[
                    "help_text"
                ] += f"open orders created between {start_date} and {end_date}."
            else:
                orders = orders.filter(created_on__date=check_date)
                if start_date:
                    context["help_text"] += f"open orders created on {start_date}."
                else:
                    context["help_text"] += "open orders created today."
        elif filter_qry == "starting":
            # Displays all open orders that have an Order.EndDate LESS THAN 5 days from Today
            # starting in less than 5 days = starting T + 1-5 .. basically meaning these orders are high priority because it’s coming up on the date
            orders = orders.filter(
                Q(end_date__gte=check_date)
                & Q(end_date__lte=check_date + datetime.timedelta(days=5))
            )
            if start_date:
                context[
                    "help_text"
                ] += f"open orders expiring (Order.EndDate) within 5 days after {check_date}."
            else:
                context[
                    "help_text"
                ] += "open orders expiring (Order.EndDate) within 5 days."
        elif filter_qry == "inactive":
            # Displays all open orders that haven't been updated in GREATER THAN 5 days & today is BEFORE any order's Order.EndDate
            orders = orders.filter(
                Q(updated_on__date__lt=check_date - datetime.timedelta(days=5))
                & Q(end_date__lt=check_date)
            )
            if start_date:
                context[
                    "help_text"
                ] += f"open orders that haven't been updated in more than 5 days & {check_date} is after any order's EndDate."
            else:
                context[
                    "help_text"
                ] += "open orders that haven't been updated in more than 5 days & today is after any order's EndDate."
        elif filter_qry == "expired":
            # Displays all open orders that have an Order.EndDate AFTER Today
            # expired = T - infinite .. basically these are in the last and we will start working to clear this list becuase it’s an error or expired quote now
            orders = orders.filter(end_date__lt=check_date)
            if start_date:
                context[
                    "help_text"
                ] += f"open orders that have an Order.EndDate before {check_date}."
            else:
                context[
                    "help_text"
                ] += "open orders that have an Order.EndDate before Today."
        else:
            # active: default filter. Displays all open orders
            if start_date and end_date:
                orders = orders.filter(
                    Q(end_date__gte=start_date) & Q(end_date__lte=end_date)
                )
                context[
                    "help_text"
                ] += f"open orders starting on or between {start_date} and {end_date}."
            elif start_date:
                orders = orders.filter(end_date__gte=start_date)
                context[
                    "help_text"
                ] += f"open orders starting on or after {start_date}."
            elif end_date:
                orders = orders.filter(end_date__lte=end_date)
                context[
                    "help_text"
                ] += f"open orders starting on or before {start_date}."
            else:
                context["help_text"] += "open orders."

        orders = orders.prefetch_related("order_line_items")
        orders = orders.select_related(
            "order_group__seller_product_seller_location__seller_product__seller",
            "order_group__user_address",
            "order_group__user",
            "order_group__seller_product_seller_location__seller_product__product__main_product",
        )
        orders = orders.order_by("-end_date")

        if not orders:
            # messages.error(request, "Your cart is empty.")
            pass
        else:
            # Get unique order group objects from the orders and place them in address buckets.
            for order in orders:
                customer_price = order.customer_price()
                # Create a new address bucket if it doesn't exist.
                uaid = order.order_group.user_address_id
                if context["cart"].get(uaid, None) is None:
                    context["cart"][uaid] = {
                        "address": order.order_group.user_address,
                        "total": 0,
                        "transactions": [],
                        "ids": [],
                        "count": 0,
                        "show_quote": False,
                    }
                # Transactions are the individual orders (delivery/swap/removal) in the order group.
                context["cart"][uaid]["transactions"].append(order)
                context["cart"][uaid]["ids"].append(str(order.id))
                context["cart"][uaid]["count"] += 1
                context["cart"][uaid]["total"] += customer_price
                if order.order_type == Order.Type.DELIVERY:
                    context["cart"][uaid]["show_quote"] = True
                    # # Hide the quote button if this event is part of an active quote.
                    # if order.checkout_order and not order.checkout_order.is_stale:
                    #     context["cart"][uaid]["show_quote"] = False
                context["subtotal"] += customer_price
                context["cart_count"] += 1
            for addr in context["cart"]:
                supplier_total = 0
                # context["cart"][addr]["show_quote"] = True
                checkout_order = None
                for event in context["cart"][addr]["transactions"]:
                    if event.checkout_order:
                        checkout_order = event.checkout_order
                    supplier_total += event.seller_price()
                if (
                    checkout_order
                    and supplier_total == checkout_order.seller_price
                    and checkout_order.quote_expiration
                ):
                    context["cart"][addr]["show_quote"] = False
                    context["cart"][addr]["quote_sent_on"] = checkout_order.updated_on
        return render(request, "customer_dashboard/new_order/cart_list.html", context)

    context["cart_link"] = f"{reverse('customer_cart')}?{query_params.urlencode()}"
    return render(
        request,
        "customer_dashboard/new_order/cart.html",
        context,
    )


@login_required(login_url="/admin/login/")
@catch_errors()
def new_order_6(request, order_group_id):
    context = get_user_context(request)
    order_group = OrderGroup.objects.filter(id=order_group_id).first()
    if order_group:
        order_group.delete()
        messages.success(request, "Order removed from cart.")
    else:
        messages.error(request, f"Order not found [{order_group_id}].")
    return HttpResponseRedirect(reverse("customer_new_order"))


@api_view(["GET"])
@authentication_classes([])
@permission_classes([])
def accept_quote(request):
    # Accept the quote.
    cart_id = request.query_params.get("cart_id", None)
    # try:
    #     cart = CheckoutOrder.objects.get(id=cart_id)
    #     cart.quote_accepted_at = timezone.now()
    #     cart.save()
    # except Cart.DoesNotExist as e:
    #     logger.error(
    #         f"accept_quote: Cart not found for cart_id[{cart_id}]",
    #         exc_info=e,
    #     )
    #     return Response("error", status=status.HTTP_404_NOT_FOUND)
    # except Exception as e:
    #     logger.error(f"accept_quote: [{e}]-data[{request.data}]", exc_info=e)
    #     return Response("error", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return Response("OK", status=status.HTTP_200_OK)


@login_required(login_url="/admin/login/")
@catch_errors()
def show_quote(request):
    context = get_user_context(request)
    quote_id = request.GET.get("quote_id")
    # if quote_id:
    #     checkout_order = CheckoutOrder.objects.get(id=quote_id)
    #     payload = {"trigger": checkout_order.quote}
    # else:
    order_id_lst = ast.literal_eval(request.GET.get("ids"))
    checkout_order = QuoteUtils.create_quote(order_id_lst, None, quote_sent=False)
    payload = {"trigger": checkout_order.quote}
    payload["trigger"][
        "accept_url"
    ] = f"{settings.BASE_URL}/cart/{checkout_order.user_address_id}/"
    return render(request, "customer_dashboard/customer_quote.html", payload)


@login_required(login_url="/admin/login/")
def cart_send_quote(request):
    context = get_user_context(request)
    if request.method == "POST":
        # Get json body
        try:
            data = json.loads(request.body)
            email_lst = list(set(data.get("emails")))
            order_id_lst = data.get("ids")
            if email_lst and order_id_lst:
                checkout_order = QuoteUtils.create_quote(
                    order_id_lst, email_lst, quote_sent=True
                )
                data = {
                    "transactional_message_id": 4,
                    "subject": checkout_order.subject,
                    "message_data": checkout_order.quote,
                }
                data["message_data"][
                    "accept_url"
                ] = f"{settings.BASE_URL}/cart/{checkout_order.user_address_id}/"
                # https://customer.io/docs/api/app/#operation/sendEmail
                headers = {
                    "Authorization": f"Bearer {settings.CUSTOMER_IO_API_KEY}",
                    "Content-Type": "application/json",
                }
                ret_data = []
                had_error = False
                for email in email_lst:
                    data["to"] = email
                    data["identifiers"] = {"email": email}

                    json_data = json.dumps(data, cls=DecimalEncoder)
                    response = requests.post(
                        "https://api.customer.io/v1/send/email",
                        headers=headers,
                        data=json_data,
                    )
                    if response.status_code < 400:
                        ret_data.append(f"Quote sent to {email}.")
                        # resp_json = response.json()
                        # [delivery_id:{resp_json['delivery_id']}-queued_at:{resp_json['queued_at']}]
                    else:
                        had_error = True
                        resp_json = response.json()
                        ret_data.append(
                            f"Error sending quote to {email} [{resp_json['meta']['error']}]"
                        )
                if had_error:
                    return JsonResponse(
                        {"status": "error", "error": " | ".join(ret_data)}
                    )
                return JsonResponse(
                    {"status": "success", "message": " | ".join(ret_data)}
                )
            else:
                return JsonResponse(
                    {"status": "error", "error": "No email or order ids."}
                )
        except Exception as e:
            logger.error(f"Error sending quote: {e}")
            return JsonResponse({"status": "error", "error": str(e)})
    return HttpResponse(status=204)


@login_required(login_url="/admin/login/")
def make_payment_method_default(request, user_address_id, payment_method_id):
    context = get_user_context(request)
    if request.method == "POST":
        context["forloop"] = {"counter": request.POST.get("loopcount", 0)}
        if request.POST.get("is_checkout"):
            context["is_checkout"] = 1
        else:
            context["is_checkout"] = 0
        # user_address_id = request.POST.get("user_address")
        # payment_method_id = request.POST.get("payment_method")
        context["payment_method"] = PaymentMethod.objects.filter(
            id=payment_method_id
        ).first()
        context["user_address"] = UserAddress.objects.filter(id=user_address_id).first()
        if context["payment_method"] and context["user_address"]:
            context["user_address"].default_payment_method_id = context[
                "payment_method"
            ].id
            context["user_address"].save()
            setattr(context["payment_method"], "is_default", True)

        return render(
            request, "customer_dashboard/snippets/payment_method_item.html", context
        )
    else:
        return HttpResponse(status=204)


@login_required(login_url="/admin/login/")
def remove_payment_method(request, payment_method_id):
    context = get_user_context(request)
    http_status = 204
    status_text = ""
    if request.method == "POST":
        payment_method = PaymentMethod.objects.filter(id=payment_method_id).first()
        if payment_method:
            try:
                payment_method.delete()
                http_status = 200
            except Exception as e:
                http_status = 400
                status_text = f"Error deleting payment method: {e}"
        else:
            http_status = 400
            status_text = "Payment method not found."

    return HttpResponse(status=http_status, content=status_text)


@login_required(login_url="/admin/login/")
def add_payment_method(request):
    context = get_user_context(request)
    http_status = 204
    if request.method == "POST":
        user_address_id = request.POST.get("user_address")
        user_group_id = request.POST.get("user_group")
        if user_address_id:
            context["user_address"] = UserAddress.objects.filter(
                id=user_address_id
            ).first()
        # If staff, then get the user and user_group from the user_address.
        # If impersonating, then user and user_group are already set.
        if request.user.is_staff and not is_impersonating(request):
            if user_address_id:
                context["user_group"] = context["user_address"].user_group
            else:
                context["user_group"] = UserGroup.objects.filter(
                    id=user_group_id
                ).first()
            context["user"] = (
                context["user_group"].users.filter(type=UserType.ADMIN).first()
            )
            if not context["user"]:
                context["user"] = context["user_group"].users.first()
        token = request.POST.get("token")
        if token:
            if context["user"] and context["user_group"]:
                # TODO: PaymentMethodUserAddress
                payment_method = PaymentMethod(
                    user=context["user"], user_group=context["user_group"], token=token
                )
                payment_method.save()
                if user_address_id:
                    context["user_address"].default_payment_method_id = (
                        payment_method.id
                    )
                    context["user_address"].save()
                messages.success(request, "Payment method added.")
                http_status = 201

            else:
                if not context["user"]:
                    messages.error(request, "Unable to save card. User not found.")
                elif not context["user_group"]:
                    messages.error(request, "Unable to save card. Company not found.")
                http_status = 400

    return HttpResponse(status=http_status)


@login_required(login_url="/admin/login/")
@catch_errors()
def checkout(request, user_address_id):
    context = get_user_context(request)
    context["user_address"] = UserAddress.objects.filter(id=user_address_id).first()
    context["is_checkout"] = 1
    # Get all orders in the cart for this user_address_id.
    orders = get_booking_objects(
        request, context["user"], context["user_group"], exclude_in_cart=False
    )
    orders = orders.filter(order_group__user_address_id=user_address_id)
    orders = orders.filter(submitted_on__isnull=True)
    orders = orders.prefetch_related("order_line_items")
    orders = orders.order_by("-order_group__start_date")

    if request.method == "POST":
        # Save access details to the user address.
        payment_method_id = request.POST.get("payment_method")
        estimated_taxes = request.POST.get("estimated_taxes")
        if payment_method_id:
            # TODO: If the payment method is not added to the user address, then how would we know which payment method to use?
            # For now always set as default.
            if payment_method_id == "paylater":
                pass
            else:
                context["user_address"].default_payment_method_id = payment_method_id
                context["user_address"].save()
            checkout_order = None
            order_id_lst = []
            customer_price = 0
            seller_price = 0
            for order in orders:
                seller_price += order.seller_price()
                customer_price += order.customer_price()
                order_id_lst.append(order.id)
                if not checkout_order and order.checkout_order:
                    checkout_order = order.checkout_order
                order.submit_order(override_approval_policy=True)
            # TODO: Create checkout
            if checkout_order:
                if payment_method_id == "paylater":
                    checkout_order.pay_later = True
                else:
                    checkout_order.payment_method = context[
                        "user_address"
                    ].default_payment_method

                checkout_order.take_rate = order.order_group.take_rate
                checkout_order.save()
            else:
                checkout_order = CheckoutOrder(
                    user_address=context["user_address"],
                    customer_price=customer_price,
                    seller_price=seller_price,
                    estimated_taxes=estimated_taxes,
                )
                if payment_method_id == "paylater":
                    checkout_order.pay_later = True
                else:
                    checkout_order.payment_method = context[
                        "user_address"
                    ].default_payment_method
                # Update events to point to the checkout order
                Order.objects.filter(id__in=order_id_lst).update(
                    checkout_order=checkout_order
                )
            messages.success(request, "Successfully checked out!")
            return HttpResponseRedirect(reverse("customer_cart"))
        else:
            messages.error(request, "No payment method selected.")
            context["form_error"] = "No payment method selected."
        if request.POST.get("access_details") != context["user_address"].access_details:
            context["user_address"].access_details = request.POST.get("access_details")
            context["user_address"].save()
            messages.success(request, "Access details saved.")

    context["cart"] = []
    context["discounts"] = 0
    context["subtotal"] = 0
    context["cart_count"] = 0
    context["pre_tax_subtotal"] = 0
    if context["user_group"]:
        payment_methods = PaymentMethod.objects.filter(
            user_group_id=context["user_group"].id
        )
    else:
        if context["user_address"].user_group_id:
            payment_methods = PaymentMethod.objects.filter(
                user_group_id=context["user_address"].user_group_id
            )
        elif context["user_address"].user_id:
            payment_methods = PaymentMethod.objects.filter(
                user_id=context["user_address"].user_id
            )
        else:
            payment_methods = PaymentMethod.objects.filter(user_id=context["user"].id)
    # Order payment methods by newest first.
    payment_methods = payment_methods.order_by("-created_on")
    context["payment_methods"] = []
    for payment_method in payment_methods:
        if payment_method.id == context["user_address"].default_payment_method_id:
            setattr(payment_method, "is_default", True)
        context["payment_methods"].append(payment_method)
    context["needs_approval"] = False
    order_id_lst = []
    for order in orders:
        if order.status == Order.Status.ADMIN_APPROVAL_PENDING:
            context["needs_approval"] = True
        customer_price = order.customer_price()
        customer_price_full = order.full_price()
        context["subtotal"] += customer_price_full
        context["pre_tax_subtotal"] += customer_price
        context["cart"].append(
            {
                "order": order,
                "order_group": order.order_group,
                "price": customer_price,
                "count": 1,
                "order_type": order.order_type,
            }
        )
        context["cart_count"] += 1
        order_id_lst.append(order.id)
    # TODO: Use the quote to calculate the total price with tax.
    checkout_order = QuoteUtils.create_quote(order_id_lst, None, quote_sent=False)
    context["estimated_taxes"] = checkout_order.quote["estimated_taxes"]
    context["total"] = checkout_order.quote["total"]
    context["discounts"] = context["subtotal"] - context["pre_tax_subtotal"]
    if not context["cart"]:
        messages.error(request, "This Order is empty.")
        return HttpResponseRedirect(reverse("customer_cart"))
    return render(
        request,
        "customer_dashboard/new_order/checkout.html",
        context,
    )


@login_required(login_url="/admin/login/")
@catch_errors()
def profile(request):
    context = get_user_context(request)
    user = context["user"]

    if request.method == "POST":
        # NOTE: Since email is disabled, it is never POSTed,
        # so we need to copy the POST data and add the email back in. This ensures its presence in the form.
        POST_COPY = request.POST.copy()
        POST_COPY["email"] = user.email
        form = UserForm(POST_COPY, request.FILES)
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
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone": user.phone,
                "photo": user.photo,
                "email": user.email,
                "type": user.type,
            }
        )
        context["form"] = form
    return render(request, "customer_dashboard/profile.html", context)


@login_required(login_url="/admin/login/")
def order_group_swap(request, order_group_id, is_removal=False):
    context = get_user_context(request)

    order_group = OrderGroup.objects.filter(id=order_group_id).first()
    context["order_group"] = order_group
    context["is_removal"] = is_removal
    if is_removal:
        context["submit_link"] = reverse(
            "customer_order_group_removal",
            kwargs={
                "order_group_id": order_group_id,
            },
        )
    else:
        context["submit_link"] = reverse(
            "customer_order_group_swap",
            kwargs={
                "order_group_id": order_group_id,
            },
        )

    if request.method == "POST":
        try:
            form = OrderGroupSwapForm(request.POST, request.FILES)
            context["form"] = form
            if form.is_valid():
                swap_date = form.cleaned_data.get("swap_date")
                schedule_window = form.cleaned_data.get("schedule_window")
                # is_removal = form.cleaned_data.get("is_removal")
                # Create the Order object.
                if is_removal:
                    order_group.create_removal(swap_date, schedule_window)
                else:
                    order_group.create_swap(swap_date, schedule_window)
                # Add response header to let HTMX know to redirect to the cart page.
                response = HttpResponse("", status=201)
                response["HX-Redirect"] = reverse("customer_cart")
                context["form_msg"] = "Successfully saved!"
                messages.success(request, "Successfully added to cart!")
                return response
            else:
                raise InvalidFormError(form, "Invalid UserInviteForm")
        except InvalidFormError as e:
            # This will let bootstrap know to highlight the fields with errors.
            for field in e.form.errors:
                if e.form.fields[field].widget.attrs.get("class", None) is None:
                    e.form.fields[field].widget.attrs["class"] = "is-invalid"
                else:
                    e.form.fields[field].widget.attrs["class"] += " is-invalid"
        except Exception as e:
            context["form_error"] = (
                f"Error saving, please contact us if this continues: [{e}]."
            )
    else:
        context["form"] = OrderGroupSwapForm(
            initial={
                "order_group_id": order_group.id,
                "order_group_start_date": order_group.start_date,
            }
        )

    return render(request, "customer_dashboard/snippets/order_group_swap.html", context)


@login_required(login_url="/admin/login/")
@catch_errors()
def my_order_groups(request):
    context = get_user_context(request)
    pagination_limit = 25
    page_number = 1
    if request.GET.get("p", None) is not None:
        page_number = request.GET.get("p")
    date = request.GET.get("date", None)
    location_id = request.GET.get("location_id", None)
    user_id = request.GET.get("user_id", None)
    try:
        is_active = int(request.GET.get("active", 1))
    except ValueError:
        is_active = 1
    context["is_active"] = bool(is_active)
    query_params = request.GET.copy()
    # This is an HTMX request, so respond with html snippet
    if request.headers.get("HX-Request"):
        if user_id:
            order_groups = OrderGroup.objects.filter(user_id=user_id)
        else:
            order_groups = get_order_group_objects(
                request, context["user"], context["user_group"]
            )

        if date:
            order_groups = order_groups.filter(end_date=date)
        if location_id:
            # TODO: Ask if location is user_address_id or seller_product_seller_location__seller_location_id
            order_groups = order_groups.filter(user_address_id=location_id)
        # Select related fields to reduce db queries.
        order_groups = order_groups.select_related(
            "seller_product_seller_location__seller_product__seller",
            "seller_product_seller_location__seller_product__product__main_product",
            # "user_address",
        )
        # order_groups = order_groups.prefetch_related("orders")
        order_groups = order_groups.order_by("-end_date")

        # Active orders are those that have an end_date in the future or are null (recurring orders).
        today = datetime.date.today()
        order_groups_lst = []
        for order_group in order_groups:
            if order_group.end_date and order_group.end_date < today:
                if not is_active:
                    order_groups_lst.append(order_group)
            else:
                if is_active:
                    order_groups_lst.append(order_group)

        paginator = Paginator(order_groups_lst, pagination_limit)
        page_obj = paginator.get_page(page_number)
        context["page_obj"] = page_obj

        if page_number is None:
            page_number = 1
        else:
            page_number = int(page_number)

        query_params["p"] = 1
        context["page_start_link"] = (
            f"/customer/order_groups/?{query_params.urlencode()}"
        )
        query_params["p"] = page_number
        context["page_current_link"] = (
            f"/customer/order_groups/?{query_params.urlencode()}"
        )
        if page_obj.has_previous():
            query_params["p"] = page_obj.previous_page_number()
            context["page_prev_link"] = (
                f"/customer/order_groups/?{query_params.urlencode()}"
            )
        if page_obj.has_next():
            query_params["p"] = page_obj.next_page_number()
            context["page_next_link"] = (
                f"/customer/order_groups/?{query_params.urlencode()}"
            )
        query_params["p"] = paginator.num_pages
        context["page_end_link"] = f"/customer/order_groups/?{query_params.urlencode()}"

        return render(
            request, "customer_dashboard/snippets/order_groups_table.html", context
        )
    else:
        if query_params.get("active") is None:
            query_params["active"] = 1
        context["active_orders_link"] = (
            f"/customer/order_groups/?{query_params.urlencode()}"
        )
        return render(request, "customer_dashboard/order_groups.html", context)


@login_required(login_url="/admin/login/")
@catch_errors()
def order_group_detail(request, order_group_id):
    context = get_user_context(request)
    # This is an HTMX request, so respond with html snippet
    # if request.headers.get("HX-Request"):
    # order.order_group.user_address.access_details
    # order.order_group.placement_details
    order_group = OrderGroup.objects.filter(id=order_group_id)
    order_group = order_group.select_related(
        "seller_product_seller_location__seller_product__seller",
        "seller_product_seller_location__seller_product__product__main_product",
        "user_address",
    )
    order_group = order_group.prefetch_related("orders")
    order_group = order_group.first()
    context["order_group"] = order_group
    user_address = order_group.user_address
    context["user_address"] = user_address
    context["orders"] = order_group.orders.all().order_by("-end_date")

    if request.method == "POST":
        try:
            save_model = None
            if "access_details_button" in request.POST:
                context["placement_form"] = PlacementDetailsForm(
                    initial={"placement_details": order_group.placement_details}
                )
                form = AccessDetailsForm(request.POST)
                context["access_form"] = form
                if form.is_valid():
                    if (
                        form.cleaned_data.get("access_details")
                        != user_address.access_details
                    ):
                        user_address.access_details = form.cleaned_data.get(
                            "access_details"
                        )
                        save_model = user_address
                else:
                    raise InvalidFormError(form, "Invalid AccessDetailsForm")
            elif "placement_details_button" in request.POST:
                context["access_form"] = AccessDetailsForm(
                    initial={"access_details": user_address.access_details}
                )
                form = PlacementDetailsForm(request.POST)
                context["placement_form"] = form
                if form.is_valid():
                    if (
                        form.cleaned_data.get("placement_details")
                        != order_group.placement_details
                    ):
                        order_group.placement_details = form.cleaned_data.get(
                            "placement_details"
                        )
                        save_model = order_group
                else:
                    raise InvalidFormError(form, "Invalid PlacementDetailsForm")
            if save_model:
                save_model.save()
                messages.success(request, "Successfully saved!")
            else:
                messages.info(request, "No changes detected.")
            return render(
                request, "customer_dashboard/order_group_detail.html", context
            )
        except InvalidFormError as e:
            # This will let bootstrap know to highlight the fields with errors.
            for field in e.form.errors:
                if e.form.fields[field].widget.attrs.get("class", None) is None:
                    e.form.fields[field].widget.attrs["class"] = "is-invalid"
                else:
                    e.form.fields[field].widget.attrs["class"] += " is-invalid"
            # messages.error(request, "Error saving, please contact us if this continues.")
            # messages.error(request, e.msg)
    else:
        context["access_form"] = AccessDetailsForm(
            initial={"access_details": user_address.access_details}
        )
        context["placement_form"] = PlacementDetailsForm(
            initial={"placement_details": order_group.placement_details}
        )

    return render(request, "customer_dashboard/order_group_detail.html", context)


@login_required(login_url="/admin/login/")
@catch_errors()
def order_detail(request, order_id):
    context = get_user_context(request)
    order = Order.objects.filter(id=order_id)
    order = order.select_related(
        "order_group__seller_product_seller_location__seller_product__seller",
        "order_group__user_address",
        "order_group__user",
        "order_group__seller_product_seller_location__seller_product__product__main_product",
    )
    order = order.prefetch_related("payouts", "order_line_items")
    context["order"] = order.first()

    return render(request, "customer_dashboard/order_detail.html", context)


@login_required(login_url="/admin/login/")
def company_last_order(request):
    context = {}
    user_address_id = request.GET.get("user_address_id", None)
    user_group_id = request.GET.get("user_group_id", None)
    user_id = request.GET.get("user_id", None)
    if user_address_id:
        orders = Order.objects.filter(order_group__user_address_id=user_address_id)
    elif user_group_id:
        orders = Order.objects.filter(order_group__user__user_group_id=user_group_id)
    elif user_id:
        orders = Order.objects.filter(order_group__user_id=user_id)
    else:
        return HttpRequest(status=204)

    orders = orders.order_by("-end_date").first()
    context["last_order"] = orders
    # Assume htmx request, so only return html snippet
    return render(
        request, "customer_dashboard/snippets/company_last_order_col.html", context
    )


@login_required(login_url="/admin/login/")
@catch_errors()
def locations(request):
    context = get_user_context(request)
    pagination_limit = 25
    page_number = 1
    if request.GET.get("p", None) is not None:
        page_number = request.GET.get("p")
    search_q = request.GET.get("q", None)
    # location_id = request.GET.get("location_id", None)
    # This is an HTMX request, so respond with html snippet
    if request.headers.get("HX-Request"):
        tab = request.GET.get("tab", None)
        context["tab"] = tab
        query_params = request.GET.copy()

        if request.user.is_staff and tab == "new":
            user_addresses = UserAddressUtils.get_new(search_q=search_q)
            context["help_text"] = "New locations created in the last 30 days."
        elif request.user.is_staff and tab == "active":
            user_addresses = UserAddressUtils.get_active(search_q=search_q)
            context["help_text"] = "Active locations with orders in the last 30 days."
            pagination_limit = 100  # Create large limit due to long request time
        elif request.user.is_staff and (tab == "churned" or tab == "fully_churned"):
            cutoff_date = datetime.date.today() - datetime.timedelta(days=30)
            churn_date = datetime.date.today() - datetime.timedelta(days=60)
            user_addresses = UserAddressUtils.get_churning(
                search_q=search_q, tab=tab, old_date=churn_date, new_date=cutoff_date
            )
            pagination_limit = 200  # Create large limit due to long request time.
            if tab == "fully_churned":
                context["help_text"] = (
                    f"""Locations that had orders in the previous 30 day period, but no orders in the last 30 day period
                    (old: {churn_date.strftime('%B %d, %Y')} - {cutoff_date.strftime('%B %d, %Y')},
                    new: {cutoff_date.strftime('%B %d, %Y')} - {datetime.date.today().strftime('%B %d, %Y')})."""
                )
            else:
                context["help_text"] = (
                    f"""Churning locations are those with a smaller revenue when compared to the previous
                    30 day period (old: {churn_date.strftime('%B %d, %Y')} - {cutoff_date.strftime('%B %d, %Y')},
                    new: {cutoff_date.strftime('%B %d, %Y')} - {datetime.date.today().strftime('%B %d, %Y')})."""
                )
        else:
            user_addresses = get_location_objects(
                request, context["user"], context["user_group"], search_q=search_q
            )

        paginator = Paginator(user_addresses, pagination_limit)
        page_obj = paginator.get_page(page_number)
        context["page_obj"] = page_obj

        if page_number is None:
            page_number = 1
        else:
            page_number = int(page_number)

        query_params["p"] = 1
        context["page_start_link"] = f"/customer/locations/?{query_params.urlencode()}"
        query_params["p"] = page_number
        context["page_current_link"] = (
            f"/customer/locations/?{query_params.urlencode()}"
        )
        if page_obj.has_previous():
            query_params["p"] = page_obj.previous_page_number()
            context["page_prev_link"] = (
                f"/customer/locations/?{query_params.urlencode()}"
            )
        if page_obj.has_next():
            query_params["p"] = page_obj.next_page_number()
            context["page_next_link"] = (
                f"/customer/locations/?{query_params.urlencode()}"
            )
        query_params["p"] = paginator.num_pages
        context["page_end_link"] = f"/customer/locations/?{query_params.urlencode()}"
        return render(
            request, "customer_dashboard/snippets/locations_table.html", context
        )

    query_params = request.GET.copy()
    if query_params.get("tab", None) is not None:
        context["locations_table_link"] = request.get_full_path()
    else:
        # Else load pending tab as default
        context["locations_table_link"] = (
            f"{reverse('customer_companies')}?{query_params.urlencode()}"
        )
    return render(request, "customer_dashboard/locations.html", context)


@login_required(login_url="/admin/login/")
@catch_errors()
def location_detail(request, location_id):
    context = get_user_context(request)
    # This is an HTMX request, so respond with html snippet
    # if request.headers.get("HX-Request"):
    user_address = UserAddress.objects.get(id=location_id)
    context["user_address"] = user_address
    if user_address.user_group_id:
        context["users"] = User.objects.filter(user_group_id=user_address.user_group_id)
        today = datetime.date.today()
        order_groups = OrderGroup.objects.filter(user_address_id=user_address.id)
        order_groups = order_groups.select_related(
            "seller_product_seller_location__seller_product__seller",
            "seller_product_seller_location__seller_product__product__main_product",
            # "user_address",
        )
        # order_groups = order_groups.prefetch_related("orders")
        order_groups = order_groups.order_by("-end_date")
        # Active orders are those that have an end_date in the future or are null (recurring orders).
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
        # TODO: Maybe store these orders for this user in local cache so that, if see all is tapped, it will be faster.
        context["invoices"] = []
        invoices = Invoice.objects.filter(
            user_address_id=context["user_address"].id
        ).order_by("-due_date")
        if invoices.exists():
            context["invoices"] = invoices[:5]

    payment_methods = PaymentMethod.objects.filter(
        user_group_id=context["user_address"].user_group_id
    )
    # Order payment methods by newest first.
    payment_methods = payment_methods.order_by("-created_on")
    context["payment_methods"] = []
    for payment_method in payment_methods:
        if payment_method.id == context["user_address"].default_payment_method_id:
            setattr(payment_method, "is_default", True)
        context["payment_methods"].append(payment_method)

    if request.method == "POST":
        try:
            save_model = None
            form = UserAddressForm(request.POST)
            context["user_address_form"] = form
            if form.is_valid():
                if form.cleaned_data.get("name") != user_address.name:
                    user_address.name = form.cleaned_data.get("name")
                    save_model = user_address
                if form.cleaned_data.get("project_id") != user_address.project_id:
                    user_address.project_id = form.cleaned_data.get("project_id")
                    save_model = user_address
                if form.cleaned_data.get("address_type") != str(
                    user_address.user_address_type_id
                ):
                    user_address.user_address_type_id = form.cleaned_data.get(
                        "address_type"
                    )
                    save_model = user_address
                if form.cleaned_data.get("street") != user_address.street:
                    user_address.street = form.cleaned_data.get("street")
                    save_model = user_address
                if form.cleaned_data.get("city") != user_address.city:
                    user_address.city = form.cleaned_data.get("city")
                    save_model = user_address
                if form.cleaned_data.get("state") != user_address.state:
                    user_address.state = form.cleaned_data.get("state")
                    save_model = user_address
                if form.cleaned_data.get("postal_code") != user_address.postal_code:
                    user_address.postal_code = form.cleaned_data.get("postal_code")
                    save_model = user_address
                if form.cleaned_data.get("is_archived") != user_address.is_archived:
                    user_address.is_archived = form.cleaned_data.get("is_archived")
                    save_model = user_address
                if (
                    form.cleaned_data.get("access_details")
                    != user_address.access_details
                ):
                    user_address.access_details = form.cleaned_data.get(
                        "access_details"
                    )
                    save_model = user_address
                if (
                    form.cleaned_data.get("allow_saturday_delivery")
                    != user_address.allow_saturday_delivery
                ):
                    user_address.allow_saturday_delivery = form.cleaned_data.get(
                        "allow_saturday_delivery"
                    )
                    save_model = user_address
                if (
                    form.cleaned_data.get("allow_sunday_delivery")
                    != user_address.allow_sunday_delivery
                ):
                    user_address.allow_sunday_delivery = form.cleaned_data.get(
                        "allow_sunday_delivery"
                    )
                    save_model = user_address
            else:
                raise InvalidFormError(form, "Invalid UserAddressForm")
            if save_model:
                save_model.save()
                messages.success(request, "Successfully saved!")
            else:
                messages.info(request, "No changes detected.")
            return render(request, "customer_dashboard/location_detail.html", context)
        except InvalidFormError as e:
            # This will let bootstrap know to highlight the fields with errors.
            for field in e.form.errors:
                if e.form.fields[field].widget.attrs.get("class", None) is None:
                    e.form.fields[field].widget.attrs["class"] = "is-invalid"
                else:
                    e.form.fields[field].widget.attrs["class"] += " is-invalid"
            # messages.error(request, "Error saving, please contact us if this continues.")
            # messages.error(request, e.msg)
    else:
        context["form"] = AccessDetailsForm(
            initial={"access_details": user_address.access_details}
        )
        context["user_address_form"] = UserAddressForm(
            initial={
                "name": user_address.name,
                "project_id": user_address.project_id,
                "address_type": user_address.user_address_type_id,
                "street": user_address.street,
                "city": user_address.city,
                "state": user_address.state,
                "postal_code": user_address.postal_code,
                "is_archived": user_address.is_archived,
                "allow_saturday_delivery": user_address.allow_saturday_delivery,
                "allow_sunday_delivery": user_address.allow_sunday_delivery,
                "access_details": user_address.access_details,
            }
        )

    # For any request type, get the current UserUserAddress objects.
    user_user_addresses = UserUserAddress.objects.filter(
        user_address_id=location_id
    ).select_related("user")

    user_user_location_normal = []
    user_user_location_normal_ids = []
    user_user_location_admin_users = []
    for user_user_address in user_user_addresses:
        if user_user_address.user.type == UserType.ADMIN:
            user_user_location_admin_users.append(user_user_address.user.id)
        else:
            user_user_location_normal.append(user_user_address)
            user_user_location_normal_ids.append(user_user_address.user.id)

    context["user_user_addresses"] = user_user_location_normal

    # Get the list of UserGroup Users that are not already associated with the SellerLocation.
    if user_address.user_group:
        context["non_associated_users"] = (
            User.objects.filter(
                user_group=user_address.user_group,
            )
            .exclude(
                id__in=user_user_location_normal_ids,
            )
            .exclude(
                type=UserType.ADMIN,
            )
        )

        # Get ADMIN users for this UserGroup.
        admin_users = User.objects.filter(
            user_group_id=user_address.user_group.id,
            type=UserType.ADMIN,
        )
        context["location_admins"] = []
        for user in admin_users:
            if user.id in user_user_location_admin_users:
                context["location_admins"].append({"user": user, "notify": True})
            else:
                context["location_admins"].append({"user": user, "notify": False})

    return render(request, "customer_dashboard/location_detail.html", context)


@login_required(login_url="/admin/login/")
def customer_location_user_add(request, user_address_id, user_id):

    user_address = UserAddress.objects.get(id=user_address_id)
    user = User.objects.get(id=user_id)

    # Throw error if user is not in the same seller group as the seller location.
    if user.user_group != user_address.user_group:
        return HttpResponse("Unauthorized", status=401)
    else:
        UserUserAddress.objects.create(
            user=user,
            user_address=user_address,
        )
        if request.headers.get("HX-Request"):
            return render(
                request,
                "customer_dashboard/snippets/user_user_address_row.html",
                {
                    "location_admin": {"user": user, "notify": True},
                    "user_address": user_address,
                },
            )
        else:
            return redirect(
                reverse(
                    "customer_location_detail",
                    kwargs={
                        "location_id": user_address_id,
                    },
                )
            )


@login_required(login_url="/admin/login/")
def customer_location_user_remove(request, user_address_id, user_id):

    user_address = UserAddress.objects.get(id=user_address_id)
    user = User.objects.get(id=user_id)

    # Throw error if user is not in the same seller group as the seller location.
    if user.user_group != user_address.user_group:
        return HttpResponse("Unauthorized", status=401)
    else:
        UserUserAddress.objects.filter(
            user=user,
            user_address=user_address,
        ).delete()
        if request.headers.get("HX-Request"):
            return render(
                request,
                "customer_dashboard/snippets/user_user_address_row.html",
                {
                    "location_admin": {"user": user, "notify": False},
                    "user_address": user_address,
                },
            )
        else:
            return redirect(
                reverse(
                    "customer_location_detail",
                    kwargs={
                        "location_id": user_address_id,
                    },
                )
            )


@login_required(login_url="/admin/login/")
@catch_errors()
def new_location(request):
    context = get_user_context(request)
    # If staff user and not impersonating, then warn that no customer is selected.
    if request.user.is_staff and not is_impersonating(request):
        messages.warning(
            request,
            f"No customer selected! Location would be added to your account [{request.user.email}].",
        )

    if request.method == "POST":
        try:
            save_model = None
            if "user_address_submit" in request.POST:
                form = UserAddressForm(request.POST)
                context["user_address_form"] = form
                if form.is_valid():
                    name = form.cleaned_data.get("name")
                    project_id = form.cleaned_data.get("project_id")
                    address_type = form.cleaned_data.get("address_type")
                    street = form.cleaned_data.get("street")
                    city = form.cleaned_data.get("city")
                    state = form.cleaned_data.get("state")
                    postal_code = form.cleaned_data.get("postal_code")
                    is_archived = form.cleaned_data.get("is_archived")
                    access_details = form.cleaned_data.get("access_details")
                    allow_saturday_delivery = form.cleaned_data.get(
                        "allow_saturday_delivery"
                    )
                    allow_sunday_delivery = form.cleaned_data.get(
                        "allow_sunday_delivery"
                    )
                    user_address = UserAddress(
                        user_group_id=context["user"].user_group_id,
                        user_id=context["user"].id,
                        name=name,
                        project_id=project_id,
                        street=street,
                        city=city,
                        state=state,
                        country="US",
                        postal_code=postal_code,
                        is_archived=is_archived,
                        allow_saturday_delivery=allow_saturday_delivery,
                        allow_sunday_delivery=allow_sunday_delivery,
                    )
                    if address_type:
                        user_address.user_address_type_id = address_type
                    if access_details:
                        user_address.access_details = access_details
                    save_model = user_address
                else:
                    raise InvalidFormError(form, "Invalid UserAddressForm")
            if save_model:
                save_model.save()
                messages.success(request, "Successfully saved!")
                return redirect(
                    reverse(
                        "customer_location_detail",
                        kwargs={
                            "location_id": save_model.id,
                        },
                    )
                )
            else:
                messages.info(request, "No changes detected.")
                return HttpResponseRedirect(reverse("customer_locations"))

        except InvalidFormError as e:
            # This will let bootstrap know to highlight the fields with errors.
            for field in e.form.errors:
                if e.form.fields[field].widget.attrs.get("class", None) is None:
                    e.form.fields[field].widget.attrs["class"] = "is-invalid"
                else:
                    e.form.fields[field].widget.attrs["class"] += " is-invalid"
            # messages.error(request, "Error saving, please contact us if this continues.")
            # messages.error(request, e.msg)
    else:
        context["user_address_form"] = UserAddressForm()

    return render(request, "customer_dashboard/location_new_edit.html", context)


@login_required(login_url="/admin/login/")
def user_associated_locations(request, user_id):
    context = {}
    context["associated_locations"] = UserAddress.objects.filter(
        user_id=user_id
    ).count()
    # Assume htmx request
    # if request.headers.get("HX-Request"):
    return render(
        request,
        "customer_dashboard/snippets/user_associated_locations_count.html",
        context,
    )


@login_required(login_url="/admin/login/")
@catch_errors()
def users(request):
    context = get_user_context(request)
    pagination_limit = 25
    page_number = 1
    if request.GET.get("p", None) is not None:
        page_number = request.GET.get("p")
    user_id = request.GET.get("user_id", None)
    date = request.GET.get("date", None)
    search_q = request.GET.get("q", None)
    # location_id = request.GET.get("location_id", None)
    # This is an HTMX request, so respond with html snippet
    if request.headers.get("HX-Request"):
        tab = request.GET.get("tab", None)
        context["tab"] = tab
        query_params = request.GET.copy()

        if request.user.is_staff and tab == "new":
            users = UserUtils.get_new(search_q=search_q)
            context["help_text"] = "New users created in the last 30 days."
        elif request.user.is_staff and tab == "loggedin":
            users = UserUtils.get_loggedin(search_q=search_q)
            context["help_text"] = (
                "Get all users who have logged in, in the last 30 days."
            )
        elif request.user.is_staff and tab == "active":
            users = UserUtils.get_active(search_q=search_q)
            context["help_text"] = "Active users with orders in the last 30 days."
            pagination_limit = 100  # Create large limit due to long request time
        elif request.user.is_staff and (tab == "churned" or tab == "fully_churned"):
            cutoff_date = datetime.date.today() - datetime.timedelta(days=30)
            churn_date = datetime.date.today() - datetime.timedelta(days=60)
            users = UserUtils.get_churning(
                search_q=search_q, tab=tab, old_date=churn_date, new_date=cutoff_date
            )
            pagination_limit = 200  # Create large limit due to long request time.
            if tab == "fully_churned":
                context["help_text"] = (
                    f"""Users that had orders in the previous 30 day period, but no orders in the last 30 day period
                    (old: {churn_date.strftime('%B %d, %Y')} - {cutoff_date.strftime('%B %d, %Y')},
                    new: {cutoff_date.strftime('%B %d, %Y')} - {datetime.date.today().strftime('%B %d, %Y')})."""
                )
            else:
                context["help_text"] = (
                    f"""Churning users are those with a smaller revenue when compared to the previous
                    30 day period (old: {churn_date.strftime('%B %d, %Y')} - {cutoff_date.strftime('%B %d, %Y')},
                    new: {cutoff_date.strftime('%B %d, %Y')} - {datetime.date.today().strftime('%B %d, %Y')})."""
                )
        else:
            users = get_user_group_user_objects(
                request, context["user"], context["user_group"], search_q=search_q
            )
            if date:
                users = users.filter(date_joined__date=date)
            users = users.order_by("-date_joined")

        paginator = Paginator(users, pagination_limit)
        page_obj = paginator.get_page(page_number)
        context["page_obj"] = page_obj

        if page_number is None:
            page_number = 1
        else:
            page_number = int(page_number)

        query_params["p"] = 1
        context["page_start_link"] = f"/customer/users/?{query_params.urlencode()}"
        query_params["p"] = page_number
        context["page_current_link"] = f"/customer/users/?{query_params.urlencode()}"
        if page_obj.has_previous():
            query_params["p"] = page_obj.previous_page_number()
            context["page_prev_link"] = f"/customer/users/?{query_params.urlencode()}"
        if page_obj.has_next():
            query_params["p"] = page_obj.next_page_number()
            context["page_next_link"] = f"/customer/users/?{query_params.urlencode()}"
        query_params["p"] = paginator.num_pages
        context["page_end_link"] = f"/customer/users/?{query_params.urlencode()}"
        return render(request, "customer_dashboard/snippets/users_table.html", context)

    query_params = request.GET.copy()
    if query_params.get("tab", None) is not None:
        context["users_table_link"] = request.get_full_path()
    else:
        # Else load pending tab as default
        context["users_table_link"] = (
            f"{reverse('customer_users')}?{query_params.urlencode()}"
        )

    return render(request, "customer_dashboard/users.html", context)


@login_required(login_url="/admin/login/")
@catch_errors()
def user_detail(request, user_id):
    context = {}
    # This is an HTMX request, so respond with html snippet
    # if request.headers.get("HX-Request"):
    user = User.objects.get(id=user_id)
    context["user"] = user
    context["user_group"] = get_user_group(request)
    if user.user_group_id:
        context["user_addresses"] = UserAddress.objects.filter(user_id=user.id)[0:3]
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
        form = UserForm(POST_COPY, request.FILES)
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
                }
            )
            context["form"] = form
            # return HttpResponse("", status=200)
            # This is an HTMX request, so respond with html snippet
            # if request.headers.get("HX-Request"):
            return render(request, "customer_dashboard/user_detail.html", context)
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
            }
        )
        context["form"] = form

    return render(request, "customer_dashboard/user_detail.html", context)


@login_required(login_url="/admin/login/")
@catch_errors()
def new_user(request):
    context = get_user_context(request)

    # Only allow admin to create new users.
    if context["user"].type != UserType.ADMIN:
        messages.error(request, "Only admins can create new users.")
        return HttpResponseRedirect(reverse("customer_users"))

    if request.method == "POST":
        try:
            save_model = None
            POST_COPY = request.POST.copy()
            # POST_COPY["email"] = user.email
            form = UserInviteForm(POST_COPY, request.FILES, auth_user=context["user"])
            context["form"] = form
            # Default to the current user's UserGroup.
            user_group_id = context["user"].user_group_id
            if not context["user_group"] and request.user.is_staff:
                usergroup_id = request.POST.get("usergroupId")
                if usergroup_id:
                    user_group = UserGroup.objects.get(id=usergroup_id)
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
                    if user_group_id:
                        user_invite = UserGroupAdminApprovalUserInvite(
                            user_group_id=user_group_id,
                            first_name=first_name,
                            last_name=last_name,
                            email=email,
                            type=user_type,
                        )
                        save_model = user_invite
                    elif request.user.is_staff:
                        # directly create the user
                        user = User(
                            first_name=first_name,
                            last_name=last_name,
                            email=email,
                            type=user_type,
                        )
                        save_model = user
                        messages.success(request, "Directly created user.")
                    else:
                        raise ValueError(
                            f"User:[{context['user'].id}]-UserGroup:[{user_group_id}]-invite attempt:[{email}]"
                        )
            else:
                raise InvalidFormError(form, "Invalid UserInviteForm")
            if save_model:
                save_model.save()
                messages.success(request, "Successfully saved!")
            else:
                messages.info(request, "No changes detected.")
            return HttpResponseRedirect(reverse("customer_users"))
        except UserAlreadyExistsError:
            messages.error(request, "User with that email already exists.")
        except InvalidFormError as e:
            # This will let bootstrap know to highlight the fields with errors.
            for field in e.form.errors:
                if e.form.fields[field].widget.attrs.get("class", None) is None:
                    e.form.fields[field].widget.attrs["class"] = "is-invalid"
                else:
                    e.form.fields[field].widget.attrs["class"] += " is-invalid"
        except IntegrityError as e:
            if "unique constraint" in str(e):
                messages.error(request, "User with that email already exists.")
            else:
                messages.error(
                    request, "Error saving, please contact us if this continues."
                )
                messages.error(request, f"Database IntegrityError:[{e}]")
        except Exception as e:
            messages.error(
                request, "Error saving, please contact us if this continues."
            )
            messages.error(request, e)
    else:
        context["form"] = UserInviteForm(auth_user=context["user"])

    return render(request, "customer_dashboard/user_new_edit.html", context)


@login_required(login_url="/admin/login/")
@catch_errors()
def invoices(request):
    context = get_user_context(request)
    pagination_limit = 25
    page_number = 1
    if request.GET.get("p", None) is not None:
        page_number = request.GET.get("p")
    date = request.GET.get("date", None)
    location_id = request.GET.get("location_id", None)
    # This is an HTMX request, so respond with html snippet
    # if request.headers.get("HX-Request"):
    query_params = request.GET.copy()
    invoices = get_invoice_objects(request, context["user"], context["user_group"])
    if location_id:
        invoices = invoices.filter(user_address_id=location_id)
    if date:
        invoices = invoices.filter(due_date__date=date)
    invoices = invoices.order_by("-due_date")
    today = datetime.date.today()
    context["total_paid"] = 0
    context["past_due"] = 0
    context["total_open"] = 0
    for invoice in invoices:
        context["total_paid"] += invoice.amount_paid
        context["total_open"] += invoice.amount_remaining
        if invoice.due_date and invoice.due_date.date() > today:
            context["past_due"] += invoice.amount_remaining

    paginator = Paginator(invoices, pagination_limit)
    page_obj = paginator.get_page(page_number)
    context["page_obj"] = page_obj

    if page_number is None:
        page_number = 1
    else:
        page_number = int(page_number)

    query_params["p"] = 1
    context["page_start_link"] = f"/customer/invoices/?{query_params.urlencode()}"
    query_params["p"] = page_number
    context["page_current_link"] = f"/customer/invoices/?{query_params.urlencode()}"
    if page_obj.has_previous():
        query_params["p"] = page_obj.previous_page_number()
        context["page_prev_link"] = f"/customer/invoices/?{query_params.urlencode()}"
    if page_obj.has_next():
        query_params["p"] = page_obj.next_page_number()
        context["page_next_link"] = f"/customer/invoices/?{query_params.urlencode()}"
    query_params["p"] = paginator.num_pages
    context["page_end_link"] = f"/customer/invoices/?{query_params.urlencode()}"
    return render(request, "customer_dashboard/invoices.html", context)


@login_required(login_url="/admin/login/")
@catch_errors()
def companies(request):
    context = get_user_context(request)
    context["help_text"] = (
        "Companies [ list of comanies where UserGroup.Seller == NULL ]"
    )
    if not request.user.is_staff:
        return HttpResponseRedirect(reverse("customer_home"))
    pagination_limit = 25
    page_number = 1
    if request.GET.get("p", None) is not None:
        page_number = request.GET.get("p")
    search_q = request.GET.get("q", None)
    # location_id = request.GET.get("location_id", None)
    # This is an HTMX request, so respond with html snippet
    if request.headers.get("HX-Request"):
        tab = request.GET.get("tab", None)
        # TODO: If impersonating a company, then only show that company.
        context["tab"] = tab
        query_params = request.GET.copy()

        if tab == "new":
            user_groups = UserGroupUtils.get_new(search_q=search_q)
            context["help_text"] = "New Companies created in the last 30 days."
        elif tab == "active":
            user_groups = UserGroupUtils.get_active(search_q=search_q)
            context["help_text"] = "Active Companies with orders in the last 30 days."
            pagination_limit = 100
        elif tab == "churned" or tab == "fully_churned":
            cutoff_date = datetime.date.today() - datetime.timedelta(days=30)
            churn_date = datetime.date.today() - datetime.timedelta(days=60)
            user_groups = UserGroupUtils.get_churning(
                search_q=search_q, tab=tab, old_date=churn_date, new_date=cutoff_date
            )
            pagination_limit = len(user_groups)
            if tab == "fully_churned":
                context["help_text"] = (
                    f"""Companies that had orders in the previous 30 day period, but no orders in the last 30 day period
                    (old: {churn_date.strftime('%B %d, %Y')} - {cutoff_date.strftime('%B %d, %Y')},
                    new: {cutoff_date.strftime('%B %d, %Y')} - {datetime.date.today().strftime('%B %d, %Y')})."""
                )
            else:
                context["help_text"] = (
                    f"""Churning Companies are those with a smaller revenue when compared to the previous
                    30 day period (old: {churn_date.strftime('%B %d, %Y')} - {cutoff_date.strftime('%B %d, %Y')},
                    new: {cutoff_date.strftime('%B %d, %Y')} - {datetime.date.today().strftime('%B %d, %Y')})."""
                )
        else:
            user_groups = UserGroup.objects.filter(seller__isnull=True)
            if search_q:
                user_groups = user_groups.filter(name__icontains=search_q)
            user_groups = user_groups.order_by("name")

        paginator = Paginator(user_groups, pagination_limit)
        page_obj = paginator.get_page(page_number)
        context["page_obj"] = page_obj

        if page_number is None:
            page_number = 1
        else:
            page_number = int(page_number)

        query_params["p"] = 1
        context["page_start_link"] = f"/customer/companies/?{query_params.urlencode()}"
        query_params["p"] = page_number
        context["page_current_link"] = (
            f"/customer/companies/?{query_params.urlencode()}"
        )
        if page_obj.has_previous():
            query_params["p"] = page_obj.previous_page_number()
            context["page_prev_link"] = (
                f"/customer/companies/?{query_params.urlencode()}"
            )
        if page_obj.has_next():
            query_params["p"] = page_obj.next_page_number()
            context["page_next_link"] = (
                f"/customer/companies/?{query_params.urlencode()}"
            )
        query_params["p"] = paginator.num_pages
        context["page_end_link"] = f"/customer/companies/?{query_params.urlencode()}"
        return render(
            request, "customer_dashboard/snippets/companies_table.html", context
        )

    query_params = request.GET.copy()
    if query_params.get("tab", None) is not None:
        context["companies_table_link"] = request.get_full_path()
    else:
        # Else load pending tab as default
        context["companies_table_link"] = (
            f"{reverse('customer_companies')}?{query_params.urlencode()}"
        )
    return render(request, "customer_dashboard/companies.html", context)


@login_required(login_url="/admin/login/")
@catch_errors()
def company_detail(request, user_group_id=None):
    context = get_user_context(request, add_user_group=False)
    if not user_group_id:
        if request.user.type != UserType.ADMIN:
            return HttpResponseRedirect(reverse("customer_home"))
        user_group = get_user_group(request)
        if not user_group:
            if hasattr(request.user, "user_group") and request.user.user_group:
                user_group = request.user.user_group
                messages.warning(
                    request,
                    f"No customer selected! Using current staff user group [{request.user.user_group}].",
                )
            else:
                # Get first available UserGroup.
                user_group = UserGroup.objects.all().first()
                messages.warning(
                    request,
                    f"No customer selected! Using first user group found: [{user_group.name}].",
                )
    else:
        if not request.user.is_staff:
            return HttpResponseRedirect(reverse("customer_home"))
        user_group = UserGroup.objects.filter(id=user_group_id)
        user_group = user_group.prefetch_related("users", "user_addresses")
        user_group = user_group.first()
    context["user_group"] = user_group
    user_group_id = None
    if context["user_group"]:
        user_group_id = context["user_group"].id
    else:
        user_group_id = context["user"].user_group_id
    payment_methods = PaymentMethod.objects.filter(user_group_id=user_group_id)
    # Order payment methods by newest first.
    context["payment_methods"] = payment_methods.order_by("-created_on")

    if request.method == "POST":
        form = UserGroupForm(request.POST, request.FILES, user=context["user"])
        context["form"] = form
        if form.is_valid():
            save_db = False
            if form.cleaned_data.get("name") != user_group.name:
                user_group.name = form.cleaned_data.get("name")
                save_db = True
            if form.cleaned_data.get("pay_later") != user_group.pay_later:
                user_group.pay_later = form.cleaned_data.get("pay_later")
                save_db = True
            if form.cleaned_data.get("autopay") != user_group.autopay:
                user_group.autopay = form.cleaned_data.get("autopay")
                save_db = True
            if (
                form.cleaned_data.get("net_terms")
                and form.cleaned_data.get("net_terms") != user_group.net_terms
            ):
                user_group.net_terms = form.cleaned_data.get("net_terms")
                save_db = True
            if (
                form.cleaned_data.get("invoice_frequency")
                != user_group.invoice_frequency
            ):
                user_group.invoice_frequency = form.cleaned_data.get(
                    "invoice_frequency"
                )
                save_db = True
            if (
                form.cleaned_data.get("invoice_day_of_month")
                != user_group.invoice_day_of_month
            ):
                user_group.invoice_day_of_month = form.cleaned_data.get(
                    "invoice_day_of_month"
                )
                save_db = True
            if (
                form.cleaned_data.get("invoice_at_project_completion")
                != user_group.invoice_at_project_completion
            ):
                user_group.invoice_at_project_completion = form.cleaned_data.get(
                    "invoice_at_project_completion"
                )
                save_db = True
            if (
                form.cleaned_data.get("credit_line_limit")
                and form.cleaned_data.get("credit_line_limit")
                != user_group.credit_line_limit
            ):
                user_group.credit_line_limit = form.cleaned_data.get(
                    "credit_line_limit"
                )
                save_db = True
            if (
                form.cleaned_data.get("compliance_status")
                and form.cleaned_data.get("compliance_status")
                != user_group.compliance_status
            ):
                user_group.compliance_status = form.cleaned_data.get(
                    "compliance_status"
                )
                save_db = True
            if (
                form.cleaned_data.get("tax_exempt_status")
                != user_group.tax_exempt_status
            ):
                user_group.tax_exempt_status = form.cleaned_data.get(
                    "tax_exempt_status"
                )
                save_db = True

            if save_db:
                context["user_group"] = user_group
                user_group.save()
                messages.success(request, "Successfully saved!")
            else:
                messages.info(request, "No changes detected.")
            # Reload the form with the updated data since disabled fields do not POST.
            form = UserGroupForm(
                initial={
                    "name": user_group.name,
                    "pay_later": user_group.pay_later,
                    "autopay": user_group.autopay,
                    "net_terms": user_group.net_terms,
                    "invoice_frequency": user_group.invoice_frequency,
                    "invoice_day_of_month": user_group.invoice_day_of_month,
                    "invoice_at_project_completion": user_group.invoice_at_project_completion,
                    "share_code": user_group.share_code,
                    "credit_line_limit": user_group.credit_line_limit,
                    "compliance_status": user_group.compliance_status,
                    "tax_exempt_status": user_group.tax_exempt_status,
                },
                user=context["user"],
            )
            context["form"] = form
            # return HttpResponse("", status=200)
            # This is an HTMX request, so respond with html snippet
            # if request.headers.get("HX-Request"):
            return render(request, "customer_dashboard/company_detail.html", context)
        else:
            # This will let bootstrap know to highlight the fields with errors.
            for field in form.errors:
                form[field].field.widget.attrs["class"] += " is-invalid"
            # messages.error(request, "Error saving, please contact us if this continues.")
    else:
        context["form"] = UserGroupForm(
            initial={
                "name": user_group.name,
                "pay_later": user_group.pay_later,
                "autopay": user_group.autopay,
                "net_terms": user_group.net_terms,
                "invoice_frequency": user_group.invoice_frequency,
                "invoice_day_of_month": user_group.invoice_day_of_month,
                "invoice_at_project_completion": user_group.invoice_at_project_completion,
                "share_code": user_group.share_code,
                "credit_line_limit": user_group.credit_line_limit,
                "compliance_status": user_group.compliance_status,
                "tax_exempt_status": user_group.tax_exempt_status,
            },
            user=context["user"],
        )
        context["types"] = context["user"].get_allowed_user_types()
    return render(request, "customer_dashboard/company_detail.html", context)


@login_required(login_url="/admin/login/")
def user_email_check(request):
    context = {}
    context["user"] = get_user(request)
    context["help_msg"] = ""
    context["css_class"] = "form-valid"
    if request.method == "POST":
        context["email"] = request.POST.get("email")
        context["phone"] = request.POST.get("phone")
        context["first_name"] = request.POST.get("first_name")
        context["last_name"] = request.POST.get("last_name")
        context["last_name"] = request.POST.get("last_name")
        context["type"] = request.POST.get("type")
        if context["type"]:
            context["types"] = context["user"].get_allowed_user_types()
    else:
        return HttpResponse("Invalid request method.", status=400)
    if context["email"]:
        try:
            validate_email(context["email"])
            if User.objects.filter(email=context["email"].casefold()).exists():
                user = User.objects.get(email=context["email"].casefold())
                if user.user_group:
                    context["error"] = (
                        f"User [{context['email']}] already exists in UserGroup [{user.user_group.name}]."
                    )
                    context["css_class"] = "form-error"
                else:
                    context["help_msg"] = "Found existing user with that email."
                    context["email"] = user.email
                    context["phone"] = user.phone
                    context["first_name"] = user.first_name
                    context["last_name"] = user.last_name
                    context["type"] = user.type
        except ValidationError as e:
            context["error"] = f"{e}"
            context["css_class"] = "form-error"

    # Assume htmx request
    # if request.headers.get("HX-Request"):
    return render(
        request,
        "customer_dashboard/snippets/email_check.html",
        context,
    )


@login_required(login_url="/admin/login/")
@catch_errors()
def new_company(request):
    context = get_user_context(request, add_user_group=False)
    if not request.user.is_staff:
        return HttpResponseRedirect(reverse("customer_home"))
    context["user_group"] = None
    context["help_msg"] = "Enter new or existing user email."
    if request.method == "POST":
        try:
            form = UserGroupForm(request.POST, request.FILES, user=request.user)
            POST_COPY = request.POST.copy()
            if request.POST.get("type"):
                context["type"] = request.POST.get("type")
            else:
                POST_COPY["type"] = UserType.ADMIN
            context["user_form"] = UserForm(POST_COPY, request.FILES)
            context["user_form"].fields["email"].disabled = False
            context["email"] = request.POST.get("email")
            context["phone"] = request.POST.get("phone")
            context["first_name"] = request.POST.get("first_name")
            context["last_name"] = request.POST.get("last_name")
            context["form"] = form
            if form.is_valid():
                # Create New UserGroup
                user_group = UserGroup(
                    name=form.cleaned_data.get("name"),
                    pay_later=form.cleaned_data.get("pay_later"),
                    autopay=form.cleaned_data.get("autopay"),
                    net_terms=form.cleaned_data.get("net_terms"),
                    invoice_frequency=form.cleaned_data.get("invoice_frequency"),
                    invoice_day_of_month=form.cleaned_data.get("invoice_day_of_month"),
                    invoice_at_project_completion=form.cleaned_data.get(
                        "invoice_at_project_completion"
                    ),
                    credit_line_limit=form.cleaned_data.get("credit_line_limit"),
                    compliance_status=form.cleaned_data.get("compliance_status"),
                    tax_exempt_status=form.cleaned_data.get("tax_exempt_status"),
                )
                if context["user_form"].is_valid():
                    # Create New User
                    email = context["user_form"].cleaned_data.get("email")
                    if User.objects.filter(email=email.casefold()).exists():
                        user = User.objects.get(email=email.casefold())
                        if user.user_group:
                            messages.error(
                                request,
                                f"User with email [{email}] already exists in UserGroup [{user.user_group.name}].",
                            )
                        else:
                            context["user_group"] = user_group
                            user_group.save()  # Only save if User will be saved.
                            user.user_group = user_group
                            user.save()
                            messages.success(request, "Successfully saved!")
                            return HttpResponseRedirect(reverse("customer_companies"))
                    else:
                        context["user_group"] = user_group
                        user_group.save()  # Only save if User will be saved.
                        user = User(
                            first_name=context["user_form"].cleaned_data.get(
                                "first_name"
                            ),
                            last_name=context["user_form"].cleaned_data.get(
                                "last_name"
                            ),
                            email=context["user_form"].cleaned_data.get("email"),
                            type=context["user_form"].cleaned_data.get("type"),
                            user_group=user_group,
                        )
                        user.save()
                        messages.success(request, "Successfully saved!")
                        return redirect(
                            reverse(
                                "customer_company_detail",
                                kwargs={
                                    "user_group_id": user_group.id,
                                },
                            )
                        )
            else:
                # This will let bootstrap know to highlight the fields with errors.
                for field in form.errors:
                    form[field].field.widget.attrs["class"] += " is-invalid"
                messages.error(
                    request, "Error saving, please contact us if this continues."
                )
        except Exception as e:
            messages.error(
                request, f"Error saving, please contact us if this continues. [{e}]"
            )
            logger.error(f"new_company: [{e}]", exc_info=e)
    else:
        context["form"] = UserGroupForm(user=request.user)

    return render(request, "customer_dashboard/company_new.html", context)


@login_required(login_url="/admin/login/")
@catch_errors()
def company_new_user(request, user_group_id):
    context = get_user_context(request, add_user_group=False)
    context["user_group"] = UserGroup.objects.get(id=user_group_id)

    # Only allow admin to create new users.
    if context["user"].type != UserType.ADMIN:
        messages.error(request, "Only admins can create new users.")
        return HttpResponseRedirect(request.get_full_path())

    if request.method == "POST":
        try:
            save_model = None
            POST_COPY = request.POST.copy()
            # POST_COPY["email"] = user.email
            form = UserInviteForm(POST_COPY, request.FILES, auth_user=context["user"])
            context["form"] = form
            if form.is_valid():
                context["first_name"] = form.cleaned_data.get("first_name")
                context["last_name"] = form.cleaned_data.get("last_name")
                context["email"] = form.cleaned_data.get("email")
                context["type"] = form.cleaned_data.get("type")
                context["types"] = context["user"].get_allowed_user_types()
                # Check if email is already in use.
                if (
                    context["email"]
                    and User.objects.filter(email=context["email"].casefold()).exists()
                ):
                    user = User.objects.get(email=context["email"].casefold())
                    if user.user_group:
                        raise UserAlreadyExistsError()
                    else:
                        user.user_group = context["user_group"]
                        save_model = user
                else:
                    user_invite = UserGroupAdminApprovalUserInvite(
                        user_group_id=context["user_group"].id,
                        first_name=context["first_name"],
                        last_name=context["last_name"],
                        email=context["email"],
                        type=context["type"],
                    )
                    save_model = user_invite
            else:
                raise InvalidFormError(form, "Invalid UserInviteForm")
            if save_model:
                save_model.save()
                context["form_msg"] = "Successfully saved!"
                context["first_name"] = context["last_name"] = context["email"] = (
                    context["type"]
                ) = ""
        except UserAlreadyExistsError:
            context["form_error"] = "User with that email already exists."
        except InvalidFormError as e:
            # This will let bootstrap know to highlight the fields with errors.
            context["form_error"] = ""
            for field in e.form.errors:
                if e.form.fields[field].widget.attrs.get("class", None) is None:
                    e.form.fields[field].widget.attrs["class"] = "is-invalid"
                else:
                    e.form.fields[field].widget.attrs["class"] += " is-invalid"
                context["form_error"] += f"{field}: {e.form[field].errors}"
        except Exception as e:
            context["form_error"] = (
                f"Error saving, please contact us if this continues: [{e}]."
            )
            messages.error(request, e)
    else:
        context["types"] = context["user"].get_allowed_user_types()

    return render(request, "customer_dashboard/snippets/company_new_user.html", context)
