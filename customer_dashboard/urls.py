from . import views
from django.urls import path

urlpatterns = [
    path("customer/search/", views.customer_search, name="customer_search"),
    path("customer/", views.index, name="customer_home"),
    path("customer/logout/", views.customer_logout, name="customer_logout"),
    path("customer/profile/", views.profile, name="customer_profile"),
    path("customer/company/", views.profile, name="customer_company"),
    path("customer/order/add/", views.index, name="customer_new_order"),
    path("customer/order_groups/", views.my_order_groups, name="customer_order_groups"),
    path(
        "customer/order_group/<uuid:order_group_id>/",
        views.order_group_detail,
        name="customer_order_group_detail",
    ),
    path(
        "customer/order/<uuid:order_id>/",
        views.order_detail,
        name="customer_order_detail",
    ),
    path("customer/locations/", views.locations, name="customer_locations"),
    path(
        "customer/location/<uuid:location_id>/",
        views.location_detail,
        name="customer_location_detail",
    ),
    path("customer/users/", views.users, name="customer_users"),
    path(
        "customer/user/<uuid:user_id>/",
        views.user_detail,
        name="customer_user_detail",
    ),
    path("customer/invoices/", views.invoices, name="customer_invoices"),
    path(
        "customer/impersonation/start/",
        views.customer_impersonation_start,
        name="customer_impersonation_start",
    ),
    path(
        "customer/impersonation/stop/",
        views.customer_impersonation_stop,
        name="customer_impersonation_stop",
    ),
    # NEW ORDER #
    path("customer/order/new/", views.new_order, name="customer_new_order"),
    path(
        "customer/order/new/category/<uuid:category_id>/",
        views.new_order_2,
        name="customer_new_order_2",
    ),
    path(
        "customer/order/new/product/<uuid:product_id>/",
        views.new_order_3,
        name="customer_new_order_3",
    ),
]
