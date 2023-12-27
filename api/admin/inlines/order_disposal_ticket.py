from django.contrib import admin

from api.models import OrderDisposalTicket


class OrderDisposalTicketInline(admin.TabularInline):
    model = OrderDisposalTicket
    fields = ("ticket_id", "disposal_location", "waste_type", "weight")
    show_change_link = True
    extra = 0
