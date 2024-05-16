from . import views
from django.urls import path

urlpatterns = [
    path("customer/search/", views.customer_search, name="customer_search"),
    path("customer/select/", views.customer_select, name="customer_select"),
    path("customer/", views.index, name="customer_home"),
    path("customer/logout/", views.customer_logout, name="customer_logout"),
    path("customer/profile/", views.profile, name="customer_profile"),
    path("customer/company/", views.profile, name="customer_company"),
    path("customer/order/add/", views.index, name="customer_new_order"),
    path("customer/orders/", views.index, name="customer_orders"),
    path("customer/locations/", views.index, name="customer_locations"),
    path("customer/users/", views.index, name="customer_users"),
    path("customer/invoices/", views.index, name="customer_invoices"),
    path(
        "customer/messages/clear/", views.messages_clear, name="customer_messages_clear"
    ),
]
