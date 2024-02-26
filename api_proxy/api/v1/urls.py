from django.conf.urls import *
from rest_framework.routers import DefaultRouter

import payment_methods.api.v1.urls as payment_methods
import payments.api.v1.urls as payments

router = DefaultRouter()
router.registry.extend(payment_methods.router.registry)
urlpatterns = router.urls + payments.urlpatterns
