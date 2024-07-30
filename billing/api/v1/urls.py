from django.conf.urls import *
from rest_framework.routers import DefaultRouter

import billing.api.v1.views as views

router = DefaultRouter()
router.register(r"invoices", views.InvoiceViewSet)

urlpatterns = router.urls
