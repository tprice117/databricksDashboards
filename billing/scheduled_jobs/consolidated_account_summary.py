from django.utils import timezone
from django.db.models import Q
from api.models import UserGroup
from billing.models import Invoice
from billing.transactional_email.account_summary import (
    send_consolidated_account_summary,
)
from billing.typings import AccountSummary


def get_user_groups_with_open_invoices():
    # Get all UserGroups that have an Invoice with status OPEN
    user_groups_with_open_invoices = UserGroup.objects.filter(
        user_addresses__invoice__status=Invoice.Status.OPEN
    ).distinct()

    return user_groups_with_open_invoices


def get_account_summary(user_group) -> AccountSummary:
    """Get account summary for a UserGroup. This includes all invoices that are not paid
    or void, invoices that are past due, and the total credit limit minus the total balance.

    Args:
        user_group (UserGroup): The UserGroup to get the account summary for.

    Returns:
        AccountSummary:
            user_group_name: the UserGroup.name
            total_invoices_not_paid_or_void = sum of invoice.amount filtered for Invoice.status != “paid” OR “void”
            trigger.total_invoices_past_due = sum of invoice.amount filtered for Invoice.duedate before TODAY
            total_credit_limit_minus_total_balance = UserGroup.creditlinelimit minus (sum of invoice.amount filtered for Invoice.status != “paid” OR “void”)

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

    total_invoices_not_paid_or_void = sum(
        [invoice.amount_remaining for invoice in invoices]
    )

    now_midnight = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # Get all invoices for this UserGroup that are past due.
    invoices_past_due = invoices.filter(due_date__lt=now_midnight)

    total_invoices_past_due = sum(
        [invoice.amount_remaining for invoice in invoices_past_due]
    )

    # Calculate the total credit limit minus the total balance.
    if user_group.credit_line_limit:
        total_credit_limit_minus_total_balance = (
            user_group.credit_line_limit - total_invoices_not_paid_or_void
        )
    else:
        total_credit_limit_minus_total_balance = "N/A"

    account_summary: AccountSummary = {
        "user_group_name": user_group.name,
        "total_invoices_not_paid_or_void": total_invoices_not_paid_or_void,
        "total_invoices_past_due": total_invoices_past_due,
        "total_credit_limit_minus_total_balance": total_credit_limit_minus_total_balance,
        "invoices": [
            {
                "number": invoice.number,
                "invoice_due_date": invoice.due_date,
                "invoice_status": invoice.status,
                "invoice_past_due": invoice.due_date < now_midnight
                if invoice.due_date
                else False,
                "invoice_amount_due": invoice.amount_remaining,
            }
            for invoice in invoices
        ],
    }
    return account_summary


def send_account_summary_emails():
    # Get all UserGroups that have an open invoice.
    user_groups = get_user_groups_with_open_invoices()
    for user_group in user_groups:
        # Send the account summary email to all users in the UserGroup as well as Billing.
        send_to = [user.email for user in user_group.users.all()]
        if hasattr(user_group, "billing"):
            send_to.append(user_group.billing.email)
        account_summary = get_account_summary(user_group)
        send_consolidated_account_summary(send_to, account_summary)
