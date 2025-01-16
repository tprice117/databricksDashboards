from django.utils import timezone
from django.db.models import Q
from api.models import UserGroup
from billing.models import Invoice
from billing.typings import AccountPastDue
from common.utils import customerio


def get_user_groups_with_past_due_invoices():
    # Get all UserGroups that have an Invoice with status OPEN and due_date < TODAY.
    now_midnight = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    user_groups_with_past_due_invoices = UserGroup.objects.filter(
        Q(user_addresses__invoice__status=Invoice.Status.OPEN)
        & Q(user_addresses__invoice__due_date__lt=now_midnight),
    ).distinct()
    return user_groups_with_past_due_invoices


def get_account_past_due(user_group) -> AccountPastDue:
    """Get account past due summary for a UserGroup. This includes all invoices that are not paid
    or void, invoices that are past due.

    Args:
        user_group (UserGroup): The UserGroup to get the account summary for.

    Returns:
        AccountPastDue:
            user_group_name: the UserGroup.name
            total_past_due_30 = sum of invoice.amount that are 1 to 30 days past due
            total_past_due_31 = sum of invoice.amount that are 31 to 60 days past due
            total_past_due_61 = sum of invoice.amount that are 61+ days past due

        For each Invoice:
            number = invoice.number
            invoice_due_date = invoice.due_date
            invoice_status = invoice.status
            invoice_past_due = invoice.due_date before TODAY then display past due
            invoice_amount_due = invoice.amount_remaining
    """
    # Get all invoices for this UserGroup that are not paid or void.
    invoices = Invoice.objects.filter(user_address__user_group=user_group).filter(
        ~Q(status=Invoice.Status.PAID) & ~Q(status=Invoice.Status.VOID)
    )
    # Get the check buffer date (14 days ago).
    two_weeks_ago = timezone.now() - timezone.timedelta(days=14)
    # Annotate check_past_due to invoice if check_sent_at is 14 days ago.
    invoices = invoices.annotate(check_past_due=Q(check_sent_at__lt=two_weeks_ago))

    now_midnight = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # Get all invoices for this UserGroup that are past due.
    invoices_past_due = invoices.filter(due_date__lt=now_midnight).order_by("due_date")

    total_past_due_30 = 0
    total_past_due_31 = 0
    total_past_due_61 = 0
    for invoice in invoices_past_due:
        days_past_due = (now_midnight - invoice.due_date).days
        if days_past_due <= 30:
            total_past_due_30 += invoice.amount_remaining
        elif days_past_due <= 60:
            total_past_due_31 += invoice.amount_remaining
        else:
            total_past_due_61 += invoice.amount_remaining

    account_summary: AccountPastDue = {
        "user_group_name": user_group.name,
        "total_past_due_30": total_past_due_30,
        "total_past_due_31": total_past_due_31,
        "total_past_due_61": total_past_due_61,
        "invoices": [
            {
                "number": invoice.number,
                "invoice_due_date": invoice.due_date,
                "invoice_status": invoice.status,
                "check_sent_at": invoice.check_sent_at,
                "check_past_due": invoice.check_past_due,
                "invoice_past_due": invoice.due_date < now_midnight
                if invoice.due_date
                else False,
                "invoice_amount_due": invoice.amount_remaining,
            }
            for invoice in invoices_past_due
        ],
    }
    return account_summary


def send_account_past_due_emails():
    """This is a new transactional email that will be sent to UserGroup billing email.
    Trigger Logic: Every Thursday when a UserGroup has a past due invoice.
    """
    # Get all UserGroups that have an open invoice.
    user_groups = get_user_groups_with_past_due_invoices()
    for user_group in user_groups:
        # Send the account summary email to Billing.
        send_to = []
        if hasattr(user_group, "billing") and user_group.billing.email:
            send_to.append(user_group.billing.email)
        else:
            # If the UserGroup does not have a billing email, send to all users in the UserGroup.
            send_to = [user.email for user in user_group.users.all()]
        account_summary = get_account_past_due(user_group)
        subject = f"{user_group.name}'s Past Due Notice From Downstream Marketplace"
        customerio.send_email(send_to, account_summary, subject, 8)
