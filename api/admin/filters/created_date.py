import datetime

from django.contrib.admin import SimpleListFilter


class CreatedDateFilter(SimpleListFilter):
    title = "Creation Date"
    parameter_name = "created_on"

    def lookups(self, request, model_admin):
        return [
            ("today", "Today"),
            ("yesterday", "Yesterday"),
            ("7d", "Last 7 Days"),
            ("1m", "This Month"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "Today":
            return queryset.filter(created_on__date=datetime.date.today())
        elif self.value() == "Yesterday":
            return queryset.filter(
                created_on__date=datetime.date.today() - datetime.timedelta(days=1)
            )
        elif self.value() == "Last 7 Days":
            return queryset.filter(
                created_on__date__gte=datetime.date.today() - datetime.timedelta(days=7)
            )
        elif self.value() == "This Month":
            return queryset.filter(
                created_on__date__gte=datetime.date.today().replace(day=1)
            )
