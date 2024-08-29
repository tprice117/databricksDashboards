from django.db import models
from common.models import BaseModel

# Cart is all open address orders


class Cart(BaseModel):
    """A Cart is all open address orders. A Cart might have multiple CartOrders
    where each CartOrder is a single location with one or more transactions (api.Order).
    """

    user_addresses = models.ManyToManyField("api.UserAddress", related_name="carts")
    # Non active carts are considered lost, either due to user inactivity or rejection.
    active = models.BooleanField(default=True)

    def __str__(self):
        if self.active:
            return f"Active - {self.created_on.ctime()}"
        else:
            return f"Lost - {self.created_on.ctime()}"
