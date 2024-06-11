from django.db import models

from common.models import BaseModel


class ConversationUserLastViewed(BaseModel):
    """
    Stores the last time a user viewed a conversation.
    The BaseModel.updated_on field is used to store the last viewed time.
    """

    conversation = models.ForeignKey(
        "chat.Conversation",
        on_delete=models.CASCADE,
        related_name="conversation_user_last_vieweds",
    )
    user = models.ForeignKey(
        "api.User",
        on_delete=models.CASCADE,
    )

    class Meta:
        unique_together = ("conversation", "user")
