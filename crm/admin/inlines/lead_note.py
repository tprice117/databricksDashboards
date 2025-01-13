from django import forms
from django.db import models

from common.admin.inlines import BaseModelTabularInline
from crm.models import LeadNote


class LeadNoteInline(BaseModelTabularInline):
    model = LeadNote
    fields = (
        "text",
        "created_by",
        "created_on",
    )
    show_change_link = True
    extra = 1

    formfield_overrides = {
        models.TextField: {"widget": forms.Textarea(attrs={"cols": 60, "rows": 2})},
    }
