from django.conf.urls import *
from rest_framework.routers import DefaultRouter

import billing.api.v1.urls as billing
import payment_methods.api.v1.urls as payment_methods

router = DefaultRouter()
router.registry.extend(payment_methods.router.registry)
router.registry.extend(billing.router.registry)
urlpatterns = router.urls
