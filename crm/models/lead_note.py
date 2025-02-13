from django.db import models
from django.utils.translation import gettext_lazy as _

from common.models import NoteModel
from crm.models.lead import Lead


class LeadNote(NoteModel):
    """A model for capturing notes/comments about a particular lead."""

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="notes")
