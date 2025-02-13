from django.db import models
from django.utils.translation import gettext_lazy as _

from api.models.order.order_group import OrderGroup
from common.models import BaseModel


class OrderGroupNote(BaseModel):
    """
    A model for capturing notes/comments about a particular booking.
    These are for staff only and should not appear in the API.
    """

    text = models.TextField(verbose_name=_("Note Text"))
    order_group = models.ForeignKey(
        OrderGroup, on_delete=models.CASCADE, related_name="notes"
    )

    class Meta:
        verbose_name = _("Booking Note")
        verbose_name_plural = _("Booking Notes")

    def __str__(self):
        char_limit = 25
        return (
            f"{self.text[:char_limit]}..." if len(self.text) > char_limit else self.text
        )
