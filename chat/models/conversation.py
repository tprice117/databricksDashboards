from django.db import models

from api.models.user.user import User
from common.models import BaseModel


class Conversation(BaseModel):
    users = models.ManyToManyField(
        User, 
        related_name='conversations',
    )

    def __str__(self):
        return ", ".join([user.email for user in self.users.all()])
