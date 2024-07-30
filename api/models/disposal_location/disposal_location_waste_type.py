from django.db import models

from api.models.disposal_location.disposal_location import DisposalLocation
from api.models.waste_type import WasteType
from common.models import BaseModel


class DisposalLocationWasteType(BaseModel):
    disposal_location = models.ForeignKey(DisposalLocation, models.CASCADE)
    waste_type = models.ForeignKey(WasteType, models.CASCADE)
    price_per_ton = models.DecimalField(max_digits=18, decimal_places=2)

    def __str__(self):
        return self.disposal_location.name + " - " + self.waste_type.name
