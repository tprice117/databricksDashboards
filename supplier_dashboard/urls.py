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
]
