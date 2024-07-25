from django.conf.urls import *
from django.urls import path

import matching_engine.api.v1.views as views

urlpatterns = [
    path(
        "seller-product-seller-locations/",
        views.GetSellerProductSellerLocationsView.as_view(),
    ),
    path(
        "seller-product-seller-locations-by-lat-long/",
        views.GetSellerProductSellerLocationsByLatLongView.as_view(),
    ),
]
