from django.urls import path, include

from api.views import create_products_for_main_product

urlpatterns = [
    path(
        "admin/create-products-for-main-product/<uuid:main_product_id>/",
        create_products_for_main_product,
        name="create_products_for_main_product",
    ),
    path("v1/", include("api.v1.urls")),
]
