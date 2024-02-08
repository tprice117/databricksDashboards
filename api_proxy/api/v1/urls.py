from django.conf.urls import *
from rest_framework.routers import DefaultRouter

import payment_methods.api.v1.urls as payment_methods

router = DefaultRouter()
router.registry.extend(payment_methods.router.registry)
urlpatterns = router.urls
