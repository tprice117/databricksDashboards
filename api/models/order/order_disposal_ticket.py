import uuid

from django.db import models

from api.models.disposal_location.disposal_location import DisposalLocation
from api.models.order.order import Order
from api.models.waste_type import WasteType
from common.models import BaseModel


class OrderDisposalTicket(BaseModel):
    def get_file_path(instance, filename):
        ext = filename.split(".")[-1]
        filename = "%s.%s" % (uuid.uuid4(), ext)
        return filename

    order = models.ForeignKey(Order, models.PROTECT)
    waste_type = models.ForeignKey(WasteType, models.PROTECT)
    disposal_location = models.ForeignKey(
        DisposalLocation, models.PROTECT, blank=True, null=True
    )
    image = models.FileField(upload_to=get_file_path, blank=True, null=True)
    ticket_id = models.CharField(max_length=255)
    weight = models.DecimalField(max_digits=18, decimal_places=2)

    def __str__(self):
        return self.ticket_id + " - " + self.order.order_group.user_address.name

    class Meta:
        verbose_name = "Event Disposal Ticket"
        verbose_name_plural = "Event Disposal Tickets"
