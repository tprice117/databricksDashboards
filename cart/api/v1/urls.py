from django.conf.urls import *
from django.urls import path

import cart.api.v1.views as views

urlpatterns = [
    path("", views.CheckoutView.as_view(), name="checkout"),
]
