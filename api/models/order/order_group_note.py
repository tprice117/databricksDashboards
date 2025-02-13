from django.db import models
from django.utils.translation import gettext_lazy as _

from api.models.order.order_group import OrderGroup
from common.models import NoteModel


class OrderGroupNote(NoteModel):
    """
    A model for capturing notes/comments about a particular booking.
    These are for staff only and should not appear in the API.
    """

    order_group = models.ForeignKey(
        OrderGroup, on_delete=models.CASCADE, related_name="notes"
    )

    class Meta:
        verbose_name = _("Booking Note")
        verbose_name_plural = _("Booking Notes")
