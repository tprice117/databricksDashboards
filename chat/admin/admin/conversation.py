from django.contrib import admin

from chat.admin.inlines import MessageInline
from chat.models import Conversation


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    inlines = [
        MessageInline,
    ]
