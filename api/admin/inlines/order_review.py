from django.contrib import admin

from api.models import OrderReview


class OrderReviewInline(admin.StackedInline):
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
