from django.conf.urls import *
from rest_framework.routers import DefaultRouter

import payment_methods.api.v1.views as views

router = DefaultRouter()
router.register(r"payment-methods", views.PaymentMethodViewSet)
urlpatterns = router.urls
