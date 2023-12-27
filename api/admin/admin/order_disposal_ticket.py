from django.contrib import admin

from api.admin.filters.disposal_location.admin_tasks import (
    DisposalLocationAdminTasksFilter,
)
from api.models import OrderDisposalTicket


@admin.register(OrderDisposalTicket)
class OrderDisposalTicketAdmin(admin.ModelAdmin):
    model = OrderDisposalTicket
    list_filter = [
        DisposalLocationAdminTasksFilter,
    ]
