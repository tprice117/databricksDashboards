from django.contrib import admin

from api.models import OrderReview
from common.admin import BaseModelStackedInline


class OrderReviewInline(BaseModelStackedInline):
    model = OrderReview
    fields = (
        "rating",
        "professionalism",
        "communication",
        "timeliness",
        "pricing",
    )
    show_change_link = True
    extra = 0
