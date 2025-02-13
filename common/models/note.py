from django.db import models
from django.utils.translation import gettext_lazy as _

from common.models.base_model import BaseModel


class NoteModel(BaseModel):
    """A very simple model for capturing notes/comments."""

    text = models.TextField(verbose_name=_("Note Text"))

    class Meta:
        abstract = True

    def __str__(self):
        char_limit = 25
        return (
            f"{self.text[:char_limit]}..." if len(self.text) > char_limit else self.text
        )
