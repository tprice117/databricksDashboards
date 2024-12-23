from api.models import MainProductImage
from common.admin.inlines import BaseModelTabularInline


class MainProductImageInline(BaseModelTabularInline):
    model = MainProductImage
    fields = (
        "image",
        "sort",
    )
    show_change_link = True
    extra = 0
