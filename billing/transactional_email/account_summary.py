import json
from django.utils import timezone
from django.db.models import Q
from common.utils.json_encoders import DecimalFloatEncoder
from api.models import UserGroup
from billing.models import Invoice


# From issue https://downstreamsprints.atlassian.net/browse/QSP-279 (QSP-279)
# Description: This is a new transactional email that will be sent to users who have opted in to receive account summary emails.
# Trigger Logic: Every Monday when a UserGroup has a related invoice.status == “Open”


# Send to: All Users and the billing email at the company. UserGroupBilling.email & User.email for all users in the UserGroup.id this summary is for.
# CC: N/A
# BCC: N/A
# Template: Customer.io
# Liquid Text Mapping:
# {{trigger.user_group_name}} = UserGroup.Name
# {{trigger.total_invoices_not_paid_or_void}} = sum of invoice.amount filtered for Invoice.status != “paid” OR “void”
# {{trigger.total_invoices_past_due}} = sum of invoice.amount filtered for Invoice.duedate before TODAY
# ${{Total_credit_limit_minus_total_balance}} = UserGroup.creditlinelimit minus (sum of invoice.amount filtered for Invoice.status != “paid” OR “void”)
# {{trigger.invoice_id} = invoice.invoiceid
# {{trigger.invoice_due_date} = invoice.duedate
# {{trigger.invoice_status}} = invoice.status
# {{trigger.invoice_past_due}} = invoice.duedate before TODAY then display past due
# {{trigger.invoice_amount_due}} = invoice.amount


def get_user_groups_with_open_invoices():
    # Get all UserGroups that have an Invoice with status OPEN
    user_groups_with_open_invoices = UserGroup.objects.filter(
        user_addresses__invoice__status=Invoice.Status.OPEN
    ).distinct()

    return user_groups_with_open_invoices


def send_consolidated_account_summary():
    # Get all UserGroups that have an open invoice.
    user_groups = get_user_groups_with_open_invoices()

    for user_group in user_groups:
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
        total_credit_limit_minus_total_balance = (
            user_group.credit_line_limit - total_invoices_not_paid_or_void
        )

        liquid_text_mapping = {
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
        json_data = json.dumps(liquid_text_mapping, cls=DecimalFloatEncoder)
        print(json_data)
        # Send the account summary email to all users in the UserGroup as well as Billing.
        send_to = [user.email for user in user_group.users.all()]
        if hasattr(user_group, "billing"):
            send_to.append(user_group.billing.email)

        # self.send_account_summary_email(
        #     user=user_group.billing,
        #     liquid_text_mapping=liquid_text_mapping,
        # )

        print(f"Sent account summary email to {send_to}.")

    # user_groups = {}

    # for invoice in invoices:
    #     key = str(invoice.user_address.user_group.id)

    #     if key not in user_groups:
    #         if invoice.user_address.user_group.billing:
    #             billing_email = invoice.user_address.user_group.billing.email
    #         else:
    #             user = invoice.user_address.user_group.users.filter(
    #                 type="ADMIN"
    #             ).first()
    #             billing_email = user.email
    #         user_groups[key] = {
    #             "user_group": invoice.user_address.user_group.name,
    #             "billing_email": billing_email,
    #             "total_invoices_not_paid_or_void": 0,
    #             "total_invoices_past_due": 0,
    #             "total_credit_limit_minus_total_balance": 0,
    #             "invoices": [],
    #         }
    #     inv = {
    #         "invoice_id": invoice.invoice_id,
    #         "invoice_due_date": invoice.due_date,
    #         "invoice_status": invoice.status,
    #         "invoice_past_due": invoice.due_date < timezone.now().date(),
    #         "invoice_amount_due": invoice.amount,
    #     }
    #     if (
    #         invoice.status != Invoice.Status.PAID
    #         and invoice.status != Invoice.Status.VOID
    #     ):
    #         user_groups[key]["total_invoices_not_paid_or_void"] += invoice.amount
    #     if invoice.due_date < timezone.now().date():
    #         user_groups[key]["total_invoices_past_due"] += invoice.amount
    #     if invoice.user_address.user_group.credit_line_limit:
    #         user_groups[key]["total_credit_limit_minus_total_balance"] = (
    #             invoice.user_address.user_group.credit_line_limit
    #             - user_groups[key]["total_invoices_not_paid_or_void"]
    #         )
    #     user_groups[key]["invoices"].append(inv)

    # # Loop through UserGroups.
    # for ugid, summary in user_groups:
    #     users = UserGroup.objects.get(id=ugid).users.all()
    #     # # Send the account summary email to all users in the UserGroup.
    #     # for user in users:
    #     #     self.send_account_summary_email(
    #     #         user=user,
    #     #         liquid_text_mapping=liquid_text_mapping,
    #     #     )

    #     # # Send the account summary email to the billing email at the company.
    #     # self.send_account_summary_email(
    #     #     user=user_group.billing,
    #     #     liquid_text_mapping=liquid_text_mapping,
    #     # )

    #     print(f"Sent account summary email to {summary['user_group']}.")
    #     print(summary)

    # print("Finished sending account summary emails.")
