from django.utils import timezone
from api.models import User
from common.middleware.save_author import get_request
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
            return Lead.objects.bulk_update(leads_to_update, ["status", "lost_reason"])
        return 0

    @staticmethod
    def convert_customer_leads(user_address):
        return Lead.active_leads.filter(
            type=Lead.Type.CUSTOMER, user_address=user_address
        ).update(status=Lead.Status.CONVERTED)

    @staticmethod
    def convert_seller_leads(seller):
        return Lead.active_leads.filter(
            type=Lead.Type.SELLER, user__user_group__seller=seller
        ).update(status=Lead.Status.CONVERTED)

    @staticmethod
    def create_new_sign_up(user):
        """Method to automatically create a new Lead for a user upon sign up"""
        # Skips clean() method
        return Lead.objects.create(
            user=user,
            type=Lead.Type.SELLER
            if user.user_group and user.user_group.seller
            else Lead.Type.CUSTOMER,
            owner=LeadUtils.get_account_owner(user),
        )

    @staticmethod
    def create_new_location(user, user_address):
        """Method to automatically create a new Lead for a UserAddress upon creation"""
        # Skips clean() method
        lead = Lead.active_leads.filter(user=user, user_address__isnull=True).first()
        if lead:
            # Update an existing unconverted lead
            lead.user_address = user_address
            lead.status = Lead.Status.LOCATION
            lead.save()
            return lead

        return Lead.objects.create(
            user=user,
            user_address=user_address,
            type=Lead.Type.SELLER
            if user.user_group and user.user_group.seller
            else Lead.Type.CUSTOMER,
            owner=LeadUtils.get_account_owner(user, user_address=user_address),
        )

    @staticmethod
    def get_account_owner(user, user_address=None):
        """Helper to get the account owner for a user or user_address.
        This is for automatically assigning leads to Sales team members."""

        if user_address:
            # Check account owner
            if user_address.user_group and user_address.user_group.account_owner:
                return user_address.user_group.account_owner
            # Check Created By
            elif (
                user_address.created_by
                and User.sales_team_users.filter(id=user_address.created_by.id).exists()
            ):
                return user_address.created_by
        elif user.user_group and user.user_group.account_owner:
            # Check account owner
            return user.user_group.account_owner

        # Check logged_in user
        request = get_request()
        if request and getattr(request, "user", None):
            if User.sales_team_users.filter(id=request.user.id).exists():
                return request.user

        return None
