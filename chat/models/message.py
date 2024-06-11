from django.db import models

from common.models import BaseModel


class Message(BaseModel):
    conversation = models.ForeignKey(
        "chat.Conversation",
        on_delete=models.CASCADE,
        related_name="messages",
    )
    user = models.ForeignKey(
        "api.User",
        on_delete=models.CASCADE,
    )
    message = models.TextField()

    def __str__(self):
        return f"{self.user.email} - {self.created_on} - {self.message}"
