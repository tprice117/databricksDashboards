from django.utils import timezone
from crm.models.lead import Lead


class LeadUtils:
    @staticmethod
    def update_lead_statuses():
        today = timezone.now().date()
        # Get all Leads that are not CONVERTED/JUNK and have an est_conversion_date that was over 7 days ago
        leads = Lead.active_leads.filter(
            est_conversion_date__lte=(today - timezone.timedelta(days=7)),
        )
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
