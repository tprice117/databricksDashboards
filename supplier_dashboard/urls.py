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
    path("supplier/", views.index, name="supplier_home"),
    path("supplier/profile/", views.profile, name="supplier_profile"),
    path("supplier/bookings/", views.bookings, name="supplier_bookings"),
    path(
        "supplier/booking/<uuid:order_id>/",
        views.booking_detail,
        name="supplier_booking_detail",
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
