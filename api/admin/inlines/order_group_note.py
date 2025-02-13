from django import forms
from django.db import models

from common.admin.inlines import BaseModelTabularInline
from api.models import OrderGroupNote


class OrderGroupNoteInline(BaseModelTabularInline):
    model = OrderGroupNote
    fields = (
        "text",
        "created_by",
        "created_on",
        "updated_on",
    )
    show_change_link = True
    extra = 1

    formfield_overrides = {
        models.TextField: {"widget": forms.Textarea(attrs={"cols": 60, "rows": 2})},
    }
