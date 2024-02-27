import datetime

import mailchimp_transactional as MailchimpTransactional
from django.template.loader import render_to_string

from api.models import UserAddress, UserGroup
from common.utils.stripe.stripe_utils import StripeUtils


def user_group_open_invoice_reminder():
    """
    Send an email to the user group reminding them to pay their open invoices.
    """
    # Get all invoices from Stripe.
    invoices = StripeUtils.Invoice.get_all()

    # Filter to only invoices that are open.
    open_invoices = list(filter(lambda invoice: invoice["status"] == "open", invoices))

    # Get all UserGroups that have open invoices, using the 'user_group_id'
    # metadata field on the Stripe Invoice object.
    user_group_ids = list(
        map(
            lambda invoice: "user_group_id" in invoice["metadata"]
            and invoice["metadata"]["user_group_id"],
            open_invoices,
        )
    )

    # Get all UserGroups that have open invoices.
    user_groups = UserGroup.objects.filter(id__in=user_group_ids)

    # Send an email to each UserGroup.
    print("Begin sending emails to UserGroups with open invoices.")
    for user_group in user_groups:
        # Get all open invoices for this UserGroup.
        user_group_open_invoices = list(
            filter(
                lambda invoice: "user_group_id" in invoice["metadata"]
                and invoice["metadata"]["user_group_id"] == str(user_group.id),
                open_invoices,
            )
        )

        # Add formatted address to each invoice.
        for invoice in user_group_open_invoices:
            user_address_filter = UserAddress.objects.filter(
                stripe_customer_id=invoice["customer"],
            )

            if user_address_filter.exists():
                user_address = user_address_filter.first()
                invoice["formatted_address"] = user_address.formatted_address()

        # Convert invoice.amount_due to dollars (divde by 100).
        for invoice in user_group_open_invoices:
            invoice["amount_due"] = invoice["amount_due"] / 100

        # Group invoices by current, 30 days past due, 60 days past
        # due, and 90 days past due, and 90+ days past due.
        current_invoices = []
        thirty_days_past_due_invoices = []
        sixty_days_past_due_invoices = []
        ninety_days_past_due_invoices = []
        ninety_plus_days_past_due_invoices = []

        for invoice in user_group_open_invoices:
            due_date = (
                datetime.datetime.fromtimestamp(invoice["due_date"])
                if invoice["due_date"]
                else datetime.datetime.fromtimestamp(invoice["created"])
                + datetime.timedelta(days=30)
            )

            if due_date > datetime.datetime.now():
                # If the due_date is in the future, then it's
                # a current invoice.
                current_invoices.append(invoice)
            elif due_date > datetime.datetime.now() - datetime.timedelta(days=30):
                # If the due_date is within the last 30 days,
                # then it's a 30 days past due invoice.
                thirty_days_past_due_invoices.append(invoice)
            elif due_date > datetime.datetime.now() - datetime.timedelta(days=60):
                # If the due_date is within the last 60 days,
                # then it's a 60 days past due invoice.
                sixty_days_past_due_invoices.append(invoice)
            elif due_date > datetime.datetime.now() - datetime.timedelta(days=90):
                # If the due_date is within the last 90 days,
                # then it's a 90 days past due invoice.
                ninety_days_past_due_invoices.append(invoice)
            else:
                # If the due_date is more than 90 days ago,
                # then it's a 90+ days past due invoice.
                ninety_plus_days_past_due_invoices.append(invoice)

        # Get the total amount due for this UserGroup.
        total_amount_due = sum(
            map(lambda invoice: invoice["amount_due"], user_group_open_invoices)
        )

        # Structure the invoice data for the email template.
        invoice_aging_data = [
            {
                "title": "Current Invoices",
                "invoices": current_invoices,
            },
            {
                "title": "1-30 Days Past Due",
                "invoices": thirty_days_past_due_invoices,
            },
            {
                "title": "31-60 Days Past Due",
                "invoices": sixty_days_past_due_invoices,
            },
            {
                "title": "61-90 Days Past Due",
                "invoices": ninety_days_past_due_invoices,
            },
            {
                "title": "90+ Days Past Due",
                "invoices": ninety_plus_days_past_due_invoices,
            },
        ]

        # Send emails.
        if hasattr(user_group, "billing") and user_group.billing.email is not None:
            mailchimp = MailchimpTransactional.Client("md-U2XLzaCVVE24xw3tMYOw9w")
            mailchimp.messages.send(
                {
                    "message": {
                        "headers": {
                            "reply-to": "thayes@trydownstream.io",
                        },
                        "from_name": "Downstream",
                        "from_email": "billing@trydownstream.io",
                        "to": [
                            {
                                "email": user_group.billing.email,
                            },
                        ],
                        "subject": "REMINDER: You have unpaid Downstream Invoices",
                        "track_opens": True,
                        "track_clicks": True,
                        "html": render_to_string(
                            "emails/user-group-consolidated-invoice-reminder.html",
                            {
                                "user_group_name": user_group.name,
                                "total_outstanding": total_amount_due,
                                "invoice_aging_data": invoice_aging_data,
                            },
                        ),
                    }
                }
            )
