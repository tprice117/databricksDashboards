from django.utils import timezone
from crm.models.lead import Lead


class LeadUtils:
    def update_lead_statuses(self):
        leads = Lead.objects.all()
        today = timezone.now().date()
        leads_to_update = []

        for lead in leads:
            original_status = lead.status
            original_lost_reason = lead.lost_reason

            lead.update_expiration_status(today=today)

            if (
                lead.status != original_status
                or lead.lost_reason != original_lost_reason
            ):
                leads_to_update.append(lead)

        if leads_to_update:
            Lead.objects.bulk_update(leads_to_update, ["status", "lost_reason"])
            return len(leads_to_update)
        return 0
