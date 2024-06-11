from chat.models.conversation_user_last_viewed import ConversationUserLastViewed
from common.models import BaseModel


class Conversation(BaseModel):
    pass

    def view_conversation(self, current_user):
        """
        Either update the ConversationUserLastViewed, if it exists, or create a new one.
        """
        if self.conversation_user_last_vieweds.filter(user=current_user).exists():
            # Update the existing ConversationUserLastViewed.
            self.conversation_user_last_vieweds.filter(
                user=current_user,
            ).update()
        else:
            # Create a new ConversationUserLastViewed.
            ConversationUserLastViewed.objects.create(
                conversation=self,
                user=current_user,
            )
