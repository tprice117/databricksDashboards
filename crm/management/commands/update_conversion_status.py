from django.core.management.base import BaseCommand
from django.utils import timezone
from crm.models import Lead


class Command(BaseCommand):
    help = "Bulk update lead statuses based on if conversion date has passed"

    def handle(self, *args, **kwargs):
        leads = Lead.objects.all()
        today = timezone.now().date()
        leads_to_update = []

        for lead in leads:
            original_status = lead.status
            original_lost_reason = lead.lost_reason

            lead.update_conversion_status(today=today)

            if (
                lead.status != original_status
                or lead.lost_reason != original_lost_reason
            ):
                leads_to_update.append(lead)

        if leads_to_update:
            Lead.objects.bulk_update(leads_to_update, ["status", "lost_reason"])
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully updated {len(leads_to_update)} lead statuses"
                )
            )
