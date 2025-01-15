from django.db import models
from django.utils.translation import gettext_lazy as _

from common.models import BaseModel
from crm.models.lead import Lead


class LeadNote(BaseModel):
    """A model for capturing notes/comments about a particular lead."""

    text = models.TextField(_("Note Text"))
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="notes")
