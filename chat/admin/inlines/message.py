from django.contrib import admin

from chat.models import Message


class MessageInline(admin.TabularInline):
    model = Message
    fields = ("user","message","created_on",)
    readonly_fields = ("user","message","created_on",)
    show_change_link = False
    extra = 0
