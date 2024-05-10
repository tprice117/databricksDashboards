from . import views
from django.urls import path

urlpatterns = [
    path(
        "supplier/<uuid:supplier_id>/dashboard/",
        views.supplier_digest_dashboard,
        name="supplier_dashboard",
    ),
    path(
        "supplier/<uuid:supplier_id>/status/<str:status>/",
        views.supplier_digest_dashboard,
        name="supplier_dashboard",
    ),
    path("supplier/search/", views.supplier_search, name="supplier_search"),
    path("supplier/select/", views.supplier_select, name="supplier_select"),
    path("supplier/", views.index, name="supplier_home"),
    path("supplier/logout/", views.supplier_logout, name="supplier_logout"),
    path("supplier/profile/", views.profile, name="supplier_profile"),
    path("supplier/company/", views.company, name="supplier_company"),
    path("supplier/bookings/", views.bookings, name="supplier_bookings"),
    path(
        "supplier/booking/<uuid:order_id>/",
        views.booking_detail,
        name="supplier_booking_detail",
    ),
    path(
        "supplier/order/<uuid:order_id>/accept/",
        views.update_order_status,
        {"accept": True},
        name="supplier_order_accept",
    ),
    path(
        "supplier/order/<uuid:order_id>/deny/",
        views.update_order_status,
        {"accept": False},
        name="supplier_order_deny",
    ),
    path(
        "supplier/booking/<uuid:order_id>/update/",
        views.update_booking_status,
        name="supplier_booking_update",
    ),
    path("supplier/payouts/", views.payouts, name="supplier_payouts"),
    path(
        "supplier/payout/<uuid:payout_id>/",
        views.payout_detail,
        name="supplier_payout_detail",
    ),
    path("supplier/locations/", views.locations, name="supplier_locations"),
    path(
        "supplier/location/<uuid:location_id>/",
        views.location_detail,
        name="supplier_location_detail",
    ),
    path(
        "supplier/received_invoices/",
        views.received_invoices,
        name="supplier_received_invoices",
    ),
    path(
        "supplier/received_invoice/<uuid:invoice_id>/",
        views.received_invoice_detail,
        name="supplier_received_invoice_detail",
    ),
]
