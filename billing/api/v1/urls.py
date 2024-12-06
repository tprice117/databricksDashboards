from django.urls import path
from rest_framework.routers import DefaultRouter

import billing.api.v1.views as views

router = DefaultRouter()
router.register(r"invoices", views.InvoiceViewSet)
router.register(r"invoice/expanded", views.InvoiceExpandedViewSet)

urlpatterns = router.urls

urlpatterns += [
    path(
        "<uuid:order_id>/invoices/",
        views.OrderInvoiceView.as_view(),
        name="order_invoice",
    ),
    path(
        "invoice/<uuid:invoice_id>/pay/",
        views.PayInvoiceView.as_view(),
        name="invoice_pay",
    ),
]
