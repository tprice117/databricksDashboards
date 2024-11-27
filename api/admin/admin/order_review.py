from django.contrib import admin

from api.models import OrderReview
from common.admin.admin.base_admin import BaseModelAdmin


@admin.register(OrderReview)
class OrderReviewAdmin(BaseModelAdmin):
    search_fields = [
        "order__id",
    ]
    raw_id_fields = [
        "order",
    ]
    list_display = [
        "id",
        "rating",
        "professionalism",
        "communication",
        "timeliness",
        "pricing",
    ]
