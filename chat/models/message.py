from django.db import models

from api.models import User
from chat.models.conversation import Conversation
from common.models import BaseModel


class Message(BaseModel):
    conversation = models.ForeignKey(
        Conversation, 
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
    )
    message = models.TextField()

    def __str__(self):
        return f"{self.user.email} - {self.created_on} - {self.message}"
